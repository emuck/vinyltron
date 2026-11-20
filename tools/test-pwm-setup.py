"""Test PWM install/uninstall against temporary filesystem trees, never the Pi."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pwm_setup
import pwm_status


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.write('proc/asound/cards', ' 0 [Headphones ]: bcm2835_headpho - Headphones\n 5 [III ]: USB-Audio - D50 III\n')
        self.write('data/configuration/audio_interface/alsa_controller/config.json', json.dumps({'outputdevice': {'value': '5'}}))
        self.write('proc/sys/kernel/random/boot_id', 'boot-one')
        self.write('boot/userconfig.txt', '# User settings\ndtoverlay=test\n')
        self.write('boot/cmdline.txt', 'rootwait quiet\n')

    def write(self, name, text):
        file = self.root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)

    def run_setup(self, remove=False):
        with contextlib.redirect_stdout(io.StringIO()):
            pwm_setup.setup(self.root, remove)

    def test_usb_install_idempotent_and_pending_reboot_survives_reinstall(self):
        self.run_setup()
        self.run_setup()
        rule = self.root / 'etc/modprobe.d/vinyltron-matrix.conf'
        self.assertEqual(rule.read_text(), pwm_setup.RULE)
        text = (self.root / 'boot/userconfig.txt').read_text()
        self.assertEqual(text.count(pwm_setup.BLOCK), 1)
        cmdline = (self.root / 'boot/cmdline.txt').read_text()
        self.assertEqual(cmdline.count('module_blacklist=snd_bcm2835'), 1)
        state = json.loads((self.root / 'data/configuration/user_interface/vinyltron/pwm-setup.json').read_text())
        self.assertTrue(state['changed'])
        self.assertTrue(state['cmdline_added'])

    def test_onboard_audio_is_not_disabled(self):
        self.write('data/configuration/audio_interface/alsa_controller/config.json', json.dumps({'outputdevice': {'value': '0'}}))
        before = (self.root / 'boot/userconfig.txt').read_text()
        self.run_setup()
        self.assertFalse((self.root / 'etc/modprobe.d/vinyltron-matrix.conf').exists())
        self.assertEqual((self.root / 'boot/userconfig.txt').read_text(), before)
        self.assertEqual((self.root / 'boot/cmdline.txt').read_text(), 'rootwait quiet\n')

    def test_unknown_output_is_not_disabled(self):
        self.write('data/configuration/audio_interface/alsa_controller/config.json', '{}')
        self.run_setup()
        self.assertFalse((self.root / 'etc/modprobe.d/vinyltron-matrix.conf').exists())

    def test_uninstall_preserves_user_edits(self):
        self.run_setup()
        self.write('boot/userconfig.txt', (self.root / 'boot/userconfig.txt').read_text() + 'dtoverlay=later\n')
        self.run_setup(remove=True)
        self.assertFalse((self.root / 'etc/modprobe.d/vinyltron-matrix.conf').exists())
        self.assertEqual((self.root / 'boot/userconfig.txt').read_text(), '# User settings\ndtoverlay=test\ndtoverlay=later\n')
        self.assertEqual((self.root / 'boot/cmdline.txt').read_text(), 'rootwait quiet\n')

    def test_preserves_other_module_blacklist_entries_and_removes_only_ours(self):
        self.write('boot/cmdline.txt', 'rootwait module_blacklist=other quiet\n')
        self.run_setup()
        self.assertIn('module_blacklist=other,snd_bcm2835', (self.root / 'boot/cmdline.txt').read_text())
        self.run_setup(remove=True)
        self.assertEqual((self.root / 'boot/cmdline.txt').read_text(), 'rootwait module_blacklist=other quiet\n')

    def test_preserves_preexisting_module_blacklist_on_uninstall(self):
        self.write('boot/cmdline.txt', 'rootwait module_blacklist=snd_bcm2835 quiet\n')
        self.run_setup()
        self.run_setup(remove=True)
        self.assertEqual((self.root / 'boot/cmdline.txt').read_text(), 'rootwait module_blacklist=snd_bcm2835 quiet\n')

    def test_refuses_multiline_cmdline(self):
        self.write('boot/cmdline.txt', 'rootwait\nquiet\n')
        self.run_setup()
        state = json.loads((self.root / 'data/configuration/user_interface/vinyltron/pwm-setup.json').read_text())
        self.assertIn('Could not safely update', state['conflict'])
        self.assertFalse((self.root / 'etc/modprobe.d/vinyltron-matrix.conf').exists())

    def test_modified_rule_and_legacy_audio_line_are_preserved(self):
        self.write('etc/modprobe.d/vinyltron-matrix.conf', '# administrator rule\nblacklist other\n')
        self.write('boot/userconfig.txt', 'dtparam=audio=off\n')
        self.run_setup()
        self.run_setup(remove=True)
        self.assertEqual((self.root / 'etc/modprobe.d/vinyltron-matrix.conf').read_text(), '# administrator rule\nblacklist other\n')
        self.assertEqual((self.root / 'boot/userconfig.txt').read_text(), 'dtparam=audio=off\n')

    def test_boot_regeneration_does_not_remove_persistent_rule(self):
        self.run_setup()
        self.write('boot/cmdline.txt', 'snd_bcm2835.enable_hdmi=1')
        self.write('boot/userconfig.txt', '# regenerated\n')
        self.run_setup()
        self.assertEqual((self.root / 'etc/modprobe.d/vinyltron-matrix.conf').read_text(), pwm_setup.RULE)
        self.assertIn(pwm_setup.BLOCK, (self.root / 'boot/userconfig.txt').read_text())

    def test_runtime_status_is_readable_and_identifies_process(self):
        with patch.object(pwm_status, 'STATUS_PATH', self.root / 'status.json'):
            # Portable fixtures for the Linux-only process identity fields.
            original_read = pathlib.Path.read_text
            def read(path, *args, **kwargs):
                if str(path) == '/proc/sys/kernel/random/boot_id':
                    return 'test-boot'
                if str(path) == '/proc/self/stat':
                    return '42 (python) ' + ' '.join(['S'] + ['0'] * 18 + ['1234'])
                return original_read(path, *args, **kwargs)
            with patch.object(pathlib.Path, 'read_text', read):
                pwm_status.write_pwm_status('hardware', 'test')
        data = json.loads((self.root / 'status.json').read_text())
        self.assertEqual(data['mode'], 'hardware')
        self.assertEqual(data['start_ticks'], '1234')
        self.assertEqual((self.root / 'status.json').stat().st_mode & 0o777, 0o644)


if __name__ == '__main__':
    unittest.main()
