#!/usr/bin/env python3
import logging
import signal
import socket
import sys
import threading
import time
from io import BytesIO
from typing import Dict, Optional

import requests
import toml
from PIL import Image

from display import Display
from volumio_client import VolumioClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
log = logging.getLogger('vinyltron')

VERSION_PATH = 'VERSION'


FORMAT_COLORS = {
    'mp3': (0, 255, 255),
    'lossless': (255, 255, 255),
    'dsd': (220, 0, 220),
    'spotify': (0, 220, 80),
    # Reserved for future analog-source detection.
    'analog': (255, 160, 0),
}

TRACK_TYPE_CATEGORIES = {
    'mp3': 'mp3',
    'aac': 'mp3',
    'ogg': 'mp3',
    'opus': 'mp3',
    'wma': 'mp3',
    'mp4': 'mp3',
    'spotify': 'spotify',
    'spop': 'spotify',
    'webradio': 'mp3',
    'radio': 'mp3',
    'flac': 'lossless',
    'alac': 'lossless',
    'wav': 'lossless',
    'aiff': 'lossless',
    'ape': 'lossless',
    'dsd': 'dsd',
    'dsf': 'dsd',
    'dff': 'dsd',
}


FALLBACK_DELAY_SECONDS = 1.5
MPD_HOST = '127.0.0.1'
MPD_PORT = 6600
MPD_TIMEOUT_SECONDS = 0.75


class Vinyltron:
    def __init__(self, config_path: str = 'config.toml'):
        self._config_path = config_path
        self._cfg = toml.load(config_path)
        self._version = self._load_version()
        self._display = Display(self._cfg)
        self._client = VolumioClient(
            host=self._cfg['volumio']['host'],
            port=self._cfg['volumio']['port'],
            on_state=self._on_state,
        )
        self._current_albumart: Optional[str] = None
        self._current_album_key: Optional[str] = None
        self._current_track_key: Optional[str] = None
        self._pending_track_key: Optional[str] = None
        self._state_seq = 0
        self._state_lock = threading.Lock()
        self._display_on: bool = True
        self._overlay_lock = threading.Lock()
        self._badge_timer: Optional[threading.Timer] = None
        self._badge_visible = False
        self._fallback_timer: Optional[threading.Timer] = None
        self._fallback_timer_id = 0
        self._progress_timer: Optional[threading.Timer] = None
        self._progress_seek_ms = 0
        self._progress_duration_ms = 0
        self._progress_last_width: Optional[int] = None
        self._progress_playing = False
        self._progress_last_update = time.monotonic()
        self._running = True
        log.info("Vinyltron version %s", self._version)
        self._log_runtime_config("startup")
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGHUP, self._reload)

    def _on_state(self, state: Dict):
        if not self._display_on:
            return

        status = state.get('status', 'stop')
        albumart = state.get('albumart', '')

        if status not in ('play', 'pause'):
            with self._overlay_lock:
                self._schedule_fallback_locked(status)
            return

        with self._overlay_lock:
            self._cancel_fallback_locked()

        if not albumart:
            return

        track_key = self._track_key(state, albumart)
        album_key = self._album_key(state, albumart)

        with self._state_lock:
            if track_key == self._current_track_key:
                is_current_track = True
            else:
                is_current_track = False
            is_pending_track = track_key == self._pending_track_key

        if is_current_track:
            self._sync_progress_from_state(state)
            return
        if is_pending_track:
            return

        log.info("New track: %s — %s", state.get('artist'), state.get('title'))
        self._log_format_state(state)

        with self._state_lock:
            self._state_seq += 1
            seq = self._state_seq
            album_changed = album_key != self._current_album_key
            self._current_track_key = track_key
            self._pending_track_key = track_key

        with self._overlay_lock:
            self._cancel_overlay_locked()
            self._cancel_progress_locked(clear_visible=album_changed)
            if album_changed and self._badge_visible:
                self._display.clear_badge()
            self._badge_visible = False

        worker = threading.Thread(
            target=self._load_track_image,
            args=(seq, dict(state), albumart, track_key, album_key, album_changed),
            daemon=True,
            name="albumart-fetch",
        )
        worker.start()

    def _load_track_image(self, seq: int, state: Dict, albumart: str, track_key: str, album_key: str, album_changed: bool):
        img = self._fetch_albumart(albumart)
        if not self._display_on:
            return
        with self._state_lock:
            if seq != self._state_seq or track_key != self._pending_track_key:
                return

        if img:
            with self._overlay_lock:
                if album_changed or albumart != self._current_albumart:
                    self._display.show_image(img)
            with self._state_lock:
                self._current_albumart = albumart
                self._current_album_key = album_key
                self._current_track_key = track_key
                self._pending_track_key = None
            self._sync_progress_from_state(state)
            if album_changed:
                self._show_format_badge(state)
        else:
            with self._state_lock:
                if seq != self._state_seq or track_key != self._pending_track_key:
                    return
                self._current_albumart = albumart
                self._current_album_key = album_key
                self._current_track_key = track_key
                self._pending_track_key = None
            with self._overlay_lock:
                self._cancel_overlay_locked()
                self._cancel_progress_locked(clear_visible=album_changed)
                self._badge_visible = False
                self._display.show_fallback()
            log.info("Album art unavailable; showing fallback for current track")
            with self._state_lock:
                if seq != self._state_seq or track_key != self._current_track_key:
                    return
            self._sync_progress_from_state(state)
            if album_changed:
                self._show_format_badge(state)

    def _show_format_badge(self, state: Dict):
        if not self._cfg.get('overlays', {}).get('format_badge', False):
            return

        category = self._format_category(state)
        label = self._format_label(state, category)
        color_rgb = FORMAT_COLORS[category]
        duration = int(self._cfg.get('overlays', {}).get('badge_duration', 10))
        log.info("Format overlay: label=%r category=%s", label, category)

        with self._overlay_lock:
            self._cancel_overlay_locked()
            self._display.show_text(label, color_rgb)
            self._badge_visible = True
            self._badge_timer = threading.Timer(duration, self._clear_badge_from_timer)
            self._badge_timer.daemon = True
            self._badge_timer.start()

    def _format_category(self, state: Dict) -> str:
        service = self._normalized(state.get('service'))
        if service == 'spop':
            return 'spotify'

        track_type = state.get('trackType')
        if track_type is None:
            return 'mp3'

        normalized = self._normalized(track_type)
        if not normalized or normalized == 'nan':
            return 'mp3'
        if normalized == 'm4a' and state.get('bitdepth'):
            return 'lossless'

        return TRACK_TYPE_CATEGORIES.get(normalized, 'mp3')

    def _format_label(self, state: Dict, category: str) -> str:
        if category == 'spotify':
            bitrate = self._bitrate_label(state.get('bitrate')) or self._bitrate_label(state.get('samplerate'))
            codec = self._normalized(state.get('codec')).upper()
            if codec and bitrate:
                return "%s %s" % (codec, bitrate)
            return bitrate or codec or 'SPOTIFY'
        if category == 'dsd':
            return self._dsd_label(state) or 'DSD'

        track_type = self._normalized(state.get('trackType')).upper()
        if track_type == 'M4A' and state.get('bitdepth'):
            track_type = 'ALAC'
        if not track_type or track_type == 'NAN':
            track_type = 'AUDIO'

        bitrate = self._bitrate_label(state.get('bitrate'))
        bitdepth = self._bitdepth_label(state.get('bitdepth'))
        sample_rate = self._sample_rate_label(state.get('samplerate'))
        if category == 'mp3':
            if not bitrate:
                bitrate = self._mpd_bitrate_label(state)
            if bitrate:
                return "%s %s" % (track_type, bitrate)
            return track_type
        if bitdepth and sample_rate and category == 'lossless':
            return "%s/%s" % (bitdepth, sample_rate)
        if bitdepth:
            return "%s %s" % (track_type, bitdepth)
        if sample_rate and category == 'lossless':
            return "%s %s" % (track_type, sample_rate)
        return track_type

    def _bitrate_label(self, bitrate) -> Optional[str]:
        if bitrate is None:
            return None
        text = str(bitrate).strip().lower()
        if not text:
            return None
        digits = ''.join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        return "%sK" % digits

    def _mpd_bitrate_label(self, state: Dict) -> Optional[str]:
        if self._normalized(state.get('service')) != 'mpd':
            return None

        bitrate = self._mpd_status_value('bitrate')
        label = self._bitrate_label(bitrate)
        if label:
            log.info("MPD bitrate fallback: bitrate=%s label=%r", bitrate, label)
        return label

    def _mpd_status_value(self, key: str) -> Optional[str]:
        prefix = "%s:" % key
        try:
            with socket.create_connection((MPD_HOST, MPD_PORT), timeout=MPD_TIMEOUT_SECONDS) as sock:
                sock.settimeout(MPD_TIMEOUT_SECONDS)
                sock.sendall(b"status\nclose\n")
                chunks = []
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            text = b"".join(chunks).decode('utf-8', 'replace')
        except Exception as e:
            log.warning("MPD status lookup failed: %s", e)
            return None

        for line in text.splitlines():
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        return None

    def _bitdepth_label(self, bitdepth) -> Optional[str]:
        if bitdepth is None:
            return None
        digits = ''.join(ch for ch in str(bitdepth) if ch.isdigit())
        return digits or None

    def _sample_rate_label(self, samplerate) -> Optional[str]:
        if samplerate is None:
            return None
        text = str(samplerate).strip().lower().replace('khz', '').replace('hz', '')
        text = text.strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
        if value > 1000:
            value = value / 1000.0
        if abs(value - round(value)) < 0.05:
            return str(int(round(value)))
        return ("%.1f" % value).rstrip('0').rstrip('.')

    def _dsd_label(self, state: Dict) -> Optional[str]:
        for key in ('samplerate', 'bitrate'):
            text = str(state.get(key) or '').upper()
            if 'DSD' in text:
                return text.replace(' ', '')
        samplerate = self._mhz_sample_rate(state.get('samplerate'))
        if samplerate is None:
            return None
        dsd_rate = int(round(samplerate / 2.8224)) * 64
        if dsd_rate < 64:
            return None
        return "DSD%d" % dsd_rate

    def _mhz_sample_rate(self, samplerate) -> Optional[float]:
        if samplerate is None:
            return None
        text = str(samplerate).strip().lower()
        unit = 'mhz' if 'mhz' in text else 'khz' if 'khz' in text else 'hz' if 'hz' in text else ''
        text = text.replace('mhz', '').replace('khz', '').replace('hz', '').strip()
        try:
            value = float(text)
        except ValueError:
            return None
        if unit == 'khz':
            return value / 1000.0
        if unit == 'hz':
            return value / 1000000.0
        return value

    def _normalized(self, value) -> str:
        if value is None:
            return ''
        return str(value).strip().lower()

    def _track_key(self, state: Dict, albumart: str) -> str:
        parts = (
            state.get('service') or '',
            state.get('artist') or '',
            state.get('album') or '',
            state.get('title') or '',
            albumart,
        )
        return "\x1f".join(str(part) for part in parts)

    def _album_key(self, state: Dict, albumart: str) -> str:
        album = state.get('album')
        artist = state.get('albumartist') or state.get('artist')
        if album:
            return "%s\x1f%s" % (artist or '', album)
        return "%s\x1f%s" % (artist or '', albumart)

    def _clear_badge_from_timer(self):
        with self._overlay_lock:
            self._badge_timer = None
            if self._badge_visible:
                self._display.clear_badge()
                self._badge_visible = False

    def _cancel_overlay_locked(self):
        if self._badge_timer:
            self._badge_timer.cancel()
            self._badge_timer = None

    def _schedule_fallback_locked(self, status: str):
        if self._fallback_timer:
            return
        self._fallback_timer_id += 1
        timer_id = self._fallback_timer_id
        log.info(
            "Status: %s — scheduling fallback in %.1fs",
            status,
            FALLBACK_DELAY_SECONDS,
        )
        self._fallback_timer = threading.Timer(
            FALLBACK_DELAY_SECONDS,
            self._show_fallback_from_timer,
            args=(timer_id, status),
        )
        self._fallback_timer.daemon = True
        self._fallback_timer.start()

    def _cancel_fallback_locked(self):
        if self._fallback_timer:
            self._fallback_timer.cancel()
            self._fallback_timer = None
        self._fallback_timer_id += 1

    def _show_fallback_from_timer(self, timer_id: int, status: str):
        with self._overlay_lock:
            if timer_id != self._fallback_timer_id:
                return
            self._fallback_timer = None
            self._cancel_overlay_locked()
            self._cancel_progress_locked()
            self._badge_visible = False
            self._display.show_fallback()
        with self._state_lock:
            self._state_seq += 1
            self._current_albumart = None
            self._current_album_key = None
            self._current_track_key = None
            self._pending_track_key = None
        log.info("Status: %s — showing fallback", status)

    def _sync_progress_from_state(self, state: Dict):
        if self._progress_height() <= 0:
            with self._overlay_lock:
                self._cancel_progress_locked(clear_visible=True)
            return

        duration_ms = self._duration_ms(state.get('duration'))
        seek_ms = self._seek_ms(state.get('seek'))
        status = state.get('status', 'stop')

        if duration_ms <= 0:
            with self._overlay_lock:
                self._cancel_progress_locked(clear_visible=True)
            return

        with self._overlay_lock:
            was_playing = self._progress_playing
            old_duration_ms = self._progress_duration_ms
            seek_delta_ms = abs(self._progress_seek_ms - seek_ms)
            should_reschedule = (
                self._progress_timer is None or
                old_duration_ms != duration_ms or
                was_playing != (status == 'play') or
                seek_delta_ms > self._progress_seek_tolerance_ms(duration_ms)
            )

            if should_reschedule:
                self._cancel_progress_timer_locked()

            self._progress_duration_ms = duration_ms
            self._progress_seek_ms = max(0, min(duration_ms, seek_ms))
            self._progress_playing = status == 'play'
            self._progress_last_update = time.monotonic()
            self._draw_progress_locked(force=False)

            if should_reschedule and self._progress_playing and self._progress_seek_ms < self._progress_duration_ms:
                self._schedule_progress_locked()

    def _progress_tick(self):
        with self._overlay_lock:
            if not self._progress_playing or self._progress_duration_ms <= 0:
                self._progress_timer = None
                return

            now = time.monotonic()
            elapsed_ms = int((now - self._progress_last_update) * 1000)
            self._progress_seek_ms = min(
                self._progress_duration_ms,
                self._progress_seek_ms + max(0, elapsed_ms),
            )
            self._progress_last_update = now
            self._draw_progress_locked(force=False)

            self._progress_timer = None
            if self._progress_seek_ms < self._progress_duration_ms:
                self._schedule_progress_locked()

    def _draw_progress_locked(self, force: bool = False):
        width = self._progress_width()
        if not force and width == self._progress_last_width:
            return

        overlays = self._cfg.get('overlays', {})
        height = self._progress_height()
        foreground = self._rgb_tuple(overlays.get('progress_bar_foreground', [255, 255, 255]), (255, 255, 255))
        background = self._rgb_tuple(overlays.get('progress_bar_background'), None)

        self._display.show_progress(width, height, foreground, background)
        self._progress_last_width = width

    def _progress_width(self) -> int:
        if self._progress_duration_ms <= 0:
            return 0
        cols = self._progress_cols()
        return int(float(cols) * self._progress_seek_ms / self._progress_duration_ms)

    def _schedule_progress_locked(self):
        delay_ms = self._next_progress_delay_ms()
        self._progress_timer = threading.Timer(delay_ms / 1000.0, self._progress_tick)
        self._progress_timer.daemon = True
        self._progress_timer.start()

    def _next_progress_delay_ms(self) -> int:
        cols = self._progress_cols()
        current_width = self._progress_width()
        if current_width >= cols:
            return 0

        next_width = current_width + 1
        next_seek_ms = int(round(float(next_width) * self._progress_duration_ms / cols))
        return max(100, next_seek_ms - self._progress_seek_ms)

    def _cancel_progress_locked(self, clear_visible: bool = False):
        self._cancel_progress_timer_locked()
        self._progress_playing = False
        self._progress_seek_ms = 0
        self._progress_duration_ms = 0
        self._progress_last_width = None
        self._progress_last_update = time.monotonic()
        if clear_visible:
            self._display.clear_progress()

    def _cancel_progress_timer_locked(self):
        if self._progress_timer:
            self._progress_timer.cancel()
            self._progress_timer = None

    def _progress_cols(self) -> int:
        try:
            return max(1, int(self._cfg.get('display', {}).get('cols', 64)))
        except (TypeError, ValueError):
            return 64

    def _progress_height(self) -> int:
        try:
            rows = int(self._cfg.get('display', {}).get('rows', 64))
            height = int(self._cfg.get('overlays', {}).get('progress_bar_height', 3))
            return max(0, min(rows, height))
        except (TypeError, ValueError):
            return 3

    def _progress_seek_tolerance_ms(self, duration_ms: int) -> int:
        return max(1500, int(duration_ms / (self._progress_cols() * 2)))

    def _duration_ms(self, duration) -> int:
        try:
            return int(float(duration) * 1000)
        except (TypeError, ValueError):
            return 0

    def _seek_ms(self, seek) -> int:
        try:
            return int(float(seek))
        except (TypeError, ValueError):
            return 0

    def _rgb_tuple(self, value, default):
        try:
            if isinstance(value, str):
                parts = [int(part.strip()) for part in value.split(',')]
            else:
                parts = [int(part) for part in value]
            if len(parts) != 3:
                raise ValueError("RGB value must have three parts")
            return tuple(max(0, min(255, part)) for part in parts)
        except Exception:
            return default

    def _load_version(self) -> str:
        try:
            with open(VERSION_PATH, 'r') as f:
                return f.read().strip() or 'unknown'
        except Exception:
            return 'unknown'

    def _log_runtime_config(self, source: str):
        display = self._cfg.get('display', {})
        overlays = self._cfg.get('overlays', {})
        fallback = self._cfg.get('fallback', {})
        log.info(
            (
                "Config %s: display_on=%r brightness=%r gamma=%r rotation=%r "
                "hardware_mapping=%r disable_hardware_pulsing=%r slowdown_gpio=%r "
                "limit_refresh_rate_hz=%r "
                "fallback=%r fallback_mode=%r fallback_folder=%r "
                "fallback_selected=%r progress_height=%r progress_foreground=%r "
                "progress_background=%r format_badge=%r format_font=%r badge_duration=%r"
            ),
            source,
            display.get('display_on', True),
            display.get('brightness'),
            display.get('gamma'),
            display.get('rotation'),
            display.get('hardware_mapping', 'adafruit-hat-pwm'),
            display.get('disable_hardware_pulsing', False),
            display.get('slowdown_gpio'),
            display.get('limit_refresh_rate_hz', 0),
            fallback.get('image'),
            fallback.get('mode', 'single'),
            fallback.get('image_folder'),
            fallback.get('selected_image'),
            overlays.get('progress_bar_height'),
            overlays.get('progress_bar_foreground'),
            overlays.get('progress_bar_background'),
            overlays.get('format_badge'),
            overlays.get('format_font', 'tom_thumb'),
            overlays.get('badge_duration'),
        )

    def _log_format_state(self, state: Dict):
        log.info(
            "Volumio format: service=%r trackType=%r codec=%r bitrate=%r samplerate=%r bitdepth=%r",
            state.get('service'),
            state.get('trackType'),
            state.get('codec'),
            state.get('bitrate'),
            state.get('samplerate'),
            state.get('bitdepth'),
        )

    def _fetch_albumart(self, url: str) -> Optional[Image.Image]:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert('RGB')
        except Exception as e:
            log.warning("Failed to fetch albumart from %s: %s", url, e)
            return None

    def _shutdown(self, *_):
        log.info("Shutting down")
        self._running = False
        with self._overlay_lock:
            self._cancel_fallback_locked()
            self._cancel_overlay_locked()
            self._cancel_progress_locked()
            self._badge_visible = False
            self._display.clear()
        with self._state_lock:
            self._state_seq += 1
            self._pending_track_key = None
        self._client.stop()
        sys.exit(0)

    def _reload(self, *_):
        log.info("SIGHUP received — reloading config")
        try:
            self._cfg = toml.load(self._config_path)
            self._log_runtime_config("reload")
            was_on = self._display_on
            self._display_on = self._cfg['display'].get('display_on', True)
            new_format_badge = self._cfg.get('overlays', {}).get('format_badge', False)
            with self._overlay_lock:
                self._cancel_fallback_locked()
                self._cancel_overlay_locked()
                self._cancel_progress_locked(clear_visible=True)
                if not new_format_badge and self._badge_visible:
                    self._display.clear_badge()
                self._badge_visible = False
                self._display.reconfigure(self._cfg)
            if not self._display_on:
                with self._overlay_lock:
                    self._display.clear()
                with self._state_lock:
                    self._state_seq += 1
                    self._current_albumart = None
                    self._current_album_key = None
                    self._current_track_key = None
                    self._pending_track_key = None
                log.info("Display off")
            elif not was_on:
                with self._state_lock:
                    self._state_seq += 1
                    self._current_albumart = None  # force re-fetch on next state
                    self._current_album_key = None
                    self._current_track_key = None
                    self._pending_track_key = None
                self._client.request_state()
                log.info("Display on")
            else:
                with self._state_lock:
                    self._state_seq += 1
                    self._current_albumart = None
                    self._current_album_key = None
                    self._current_track_key = None
                    self._pending_track_key = None
                self._client.request_state()
                log.info("Config reloaded — requesting redisplay")
        except Exception as e:
            log.warning("Config reload failed: %s", e)

    def run(self):
        self._display.show_fallback()
        self._client.start()
        log.info("Vinyltron running")
        while self._running:
            time.sleep(1)


if __name__ == '__main__':
    config = sys.argv[1] if len(sys.argv) > 1 else 'config.toml'
    Vinyltron(config).run()
