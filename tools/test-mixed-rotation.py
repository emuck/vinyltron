"""Hardware-free scheduler regression checks. Run with Python 3.11+."""
import importlib.util
import logging
import pathlib
import sys
import tomllib
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_toml(path):
    with open(path, 'rb') as stream:
        return tomllib.load(stream)


# Replace only hardware, transport, and config-loader boundaries; execute the real
# daemon methods and real renderer classes with fake timers rather than waiting.
spec = importlib.util.spec_from_file_location('rotation_daemon', ROOT / 'vinyltron.py')
daemon = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    'display': types.SimpleNamespace(Display=MagicMock()),
    'volumio_client': types.SimpleNamespace(VolumioClient=MagicMock()),
    'toml': types.SimpleNamespace(load=load_toml),
}):
    spec.loader.exec_module(daemon)
logging.getLogger('vinyltron').disabled = True


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.signals = patch.object(daemon.signal, 'signal')
        self.signals.start()
        self.addCleanup(self.signals.stop)
        self.timers = patch.object(daemon.threading, 'Timer')
        self.timer = self.timers.start()
        self.timer.side_effect = lambda *args, **kwargs: MagicMock()
        self.addCleanup(self.timers.stop)
        self.app = daemon.Vinyltron(str(ROOT / 'config.toml'))
        self.app._cfg['fallback']['mode'] = 'mixed'
        self.app._idle_ready_to_start = lambda: True
        self.app._display = MagicMock()
        self.app._display_on = True
        self.app._cache_radar_art = MagicMock()

    def next_category(self):
        category = self.app._next_mixed_category()
        self.app._mixed_last = category
        return category

    def test_shuffle_rounds_are_fair_and_do_not_repeat_at_boundary(self):
        rounds = [[self.next_category() for _ in range(3)] for _ in range(30)]
        for group in rounds:
            self.assertEqual(set(group), {'photos', 'screensavers', 'weather'})
        for a, b in zip(rounds, rounds[1:]):
            self.assertNotEqual(a[-1], b[0])

    def test_sequential_skips_disabled_and_unavailable_art(self):
        self.app._cfg['rotation'].update(order='sequential', screensavers=False)
        self.assertEqual([self.next_category() for _ in range(4)],
                         ['photos', 'weather', 'photos', 'weather'])
        self.app._last_state = {'status': 'play', 'albumart': 'cover'}
        self.app._radar_art = daemon.Image.new('RGB', (64, 64))
        self.app._radar_art_url = 'cover'
        self.assertEqual(self.next_category(), 'album_art')
        self.app._last_state['status'] = 'pause'
        self.assertNotIn('album_art', self.app._mixed_categories())

    def test_disabled_categories_have_safe_default(self):
        self.app._cfg['rotation'].update(photos=False, screensavers=False, weather=False, album_art=False)
        self.app._start_idle_locked('stop')
        self.assertEqual(self.app._mixed_active, 'default')
        self.app._display.show_fallback.assert_called_once()

    def test_slot_timer_owns_timing_and_advances(self):
        self.app._cfg['rotation'].update(order='sequential', slot_seconds=17)
        self.app._start_idle_locked('stop')
        self.assertEqual(self.app._mixed_active, 'photos')
        timer_id = self.app._mixed_timer_id
        self.assertEqual(self.timer.call_args.args[0], 17)
        self.app._schedule_active_fallback_locked('stop')
        self.assertEqual(self.app._mixed_timer_id, timer_id)
        self.app._advance_mixed_slot(timer_id)
        self.assertEqual(self.app._mixed_active, 'screensavers')
        self.assertIsNone(self.app._screensaver_reset_timer)
        self.assertIsNone(self.app._idle_rotation_timer)

    def test_power_off_invalidates_old_callbacks(self):
        self.app._start_idle_locked('stop')
        timer_id = self.app._mixed_timer_id
        self.app._display_on = False
        self.app._clear_display_for_power_off('test')
        self.app._advance_mixed_slot(timer_id)
        self.assertIsNone(self.app._mixed_timer)
        self.assertIsNone(self.app._mixed_active)

    def test_new_album_interrupts_then_resumes_rotation(self):
        self.app._cfg['overlays']['album_art_duration'] = 10
        self.app._start_idle_locked('stop')
        old_id = self.app._mixed_timer_id
        state = {'status': 'play', 'albumart': 'cover', 'album': 'A', 'artist': 'B', 'title': 'One'}
        self.app._fetch_albumart = lambda _: daemon.Image.new('RGB', (64, 64))
        # Run artwork workers inline to deterministically exercise handoff.
        with patch.object(daemon.threading, 'Thread') as worker:
            worker.side_effect = lambda **kw: types.SimpleNamespace(start=lambda: kw['target'](*kw['args']))
            self.app._on_state(state)
            self.assertIsNone(self.app._mixed_timer)
            self.assertFalse(self.app._fallback_visible)
            self.app._advance_mixed_slot(old_id)
            self.assertFalse(self.app._fallback_visible)
            self.app._show_fallback_after_album_art_timeout(self.app._album_art_timer_id, 'play')
            self.assertTrue(self.app._fallback_visible)
            slot_id = self.app._mixed_timer_id
            self.app._on_state(dict(state, title='Two'))
            self.assertEqual(self.app._mixed_timer_id, slot_id)

    def test_album_slot_ends_on_pause(self):
        self.app._cfg['rotation'].update(photos=False, screensavers=False, weather=False)
        self.app._cfg['volumio']['artwork_enabled'] = False
        self.app._last_state = {'status': 'play', 'albumart': 'cover'}
        self.app._radar_art = daemon.Image.new('RGB', (64, 64))
        self.app._radar_art_url = 'cover'
        self.app._start_idle_locked('play')
        self.assertEqual(self.app._mixed_active, 'album_art')
        self.app._on_state({'status': 'pause', 'albumart': 'cover'})
        self.assertEqual(self.app._mixed_active, 'default')

    def test_reload_invalidates_old_slot(self):
        self.app._start_idle_locked('stop')
        timer_id = self.app._mixed_timer_id
        self.app._request_redisplay = MagicMock()
        with patch.object(daemon.toml, 'load', return_value=self.app._cfg):
            self.app._reload()
        self.app._advance_mixed_slot(timer_id)
        self.assertIsNone(self.app._mixed_timer)
        self.assertIsNone(self.app._mixed_active)

    def test_schedule_off_on_pause_cancels_rotation(self):
        self.app._start_idle_locked('stop')
        timer_id = self.app._mixed_timer_id
        self.app._schedule_allows_display = lambda: False
        self.app._on_state({'status': 'pause'})
        self.app._advance_mixed_slot(timer_id)
        self.assertFalse(self.app._display_on)
        self.assertIsNone(self.app._mixed_timer)

    def test_weather_frames_do_not_change_slot_deadline(self):
        self.app._cfg['rotation'].update(photos=False, screensavers=False, album_art=False)
        self.app._start_idle_locked('stop')
        timer_id = self.app._mixed_timer_id
        self.app._show_weather_frame_from_timer(self.app._weather_timer_id, 'stop')
        self.assertEqual(self.app._mixed_timer_id, timer_id)
        self.assertEqual(self.app._mixed_active, 'weather')


if __name__ == '__main__':
    unittest.main()
