"""Plugin-owned PWM boot protection; no module unloading or automatic reboot."""
import argparse
import json
import os
import re
import stat
import tempfile
from pathlib import Path

RULE = '# Managed by Vinyltron: reserve PWM for the LED matrix\nblacklist snd_bcm2835\ninstall snd_bcm2835 /bin/false\n'
BLOCK = '# BEGIN VINYLTRON PWM\n[all]\ndtparam=audio=off\n# END VINYLTRON PWM\n'
MODULE = 'snd_bcm2835'


def _write_atomic(path, text):
    """Replace a boot/config file atomically without leaving a partial command line."""
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chmod(temporary, mode)
        except OSError:
            # VFAT boot partitions may not support per-file mode changes.
            pass
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _cmdline_tokens(path):
    text = path.read_text()
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError('Boot command line must contain exactly one non-empty line')
    return text, lines[0].split()


def _add_module_blacklist(path):
    """Add the kernel-level blacklist needed before the real root filesystem mounts."""
    original, tokens = _cmdline_tokens(path)
    found = False
    updated = []
    for token in tokens:
        if token.startswith('module_blacklist='):
            found = True
            modules = [name for name in token.split('=', 1)[1].split(',') if name]
            if MODULE not in modules:
                modules.append(MODULE)
            token = 'module_blacklist=' + ','.join(modules)
        updated.append(token)
    if not found:
        updated.append('module_blacklist=' + MODULE)
    new_text = ' '.join(updated) + ('\n' if original.endswith('\n') else '')
    if new_text != original:
        _write_atomic(path, new_text)
        return True
    return False


def _remove_module_blacklist(path):
    """Remove only snd_bcm2835 from module_blacklist, preserving other entries."""
    try:
        original, tokens = _cmdline_tokens(path)
    except (OSError, ValueError):
        return
    updated = []
    for token in tokens:
        if token.startswith('module_blacklist='):
            modules = [name for name in token.split('=', 1)[1].split(',') if name and name != MODULE]
            if modules:
                token = 'module_blacklist=' + ','.join(modules)
                updated.append(token)
            # An empty list means there is no longer a module_blacklist option to keep.
        else:
            updated.append(token)
    new_text = ' '.join(updated) + ('\n' if original.endswith('\n') else '')
    if new_text != original:
        _write_atomic(path, new_text)


def audio_conflict(root):
    try:
        config = json.loads((root / 'data/configuration/audio_interface/alsa_controller/config.json').read_text())
        output = str(config['outputdevice']['value'])
        cards = (root / 'proc/asound/cards').read_text()
        headers = re.findall(r'^\s*(\d+)\s+\[([^]]+)\]\s*:\s*(.*)$', cards, re.M)
        selected = [header for header in headers if output in (header[0], header[1].strip())]
        if not selected:
            return 'Audio output could not be identified. Select USB/I2S audio, then reinstall Vinyltron to enable hardware PWM.'
        description = selected[0][2].lower()
        if any(name in description for name in ('bcm2835', 'bcm2711', 'vc4-hdmi')):
            return 'Onboard/HDMI audio is selected. Hardware PWM conflicts with this output. Select USB/I2S audio, then reinstall Vinyltron.'
        return None
    except (OSError, ValueError, KeyError, TypeError):
        return 'Audio output could not be verified. Select USB/I2S audio, then reinstall Vinyltron to enable hardware PWM.'


def setup(root, remove=False):
    rule = root / 'etc/modprobe.d/vinyltron-matrix.conf'
    userconfig = root / 'boot/userconfig.txt'
    state = root / 'data/configuration/user_interface/vinyltron/pwm-setup.json'
    if remove:
        # Never restore a whole old boot file over later user/Volumio changes.
        if rule.exists() and rule.read_text() == RULE:
            rule.unlink()
        elif rule.exists():
            print('WARNING: Modified vinyltron-matrix.conf preserved for administrator review.')
        if userconfig.exists():
            text = userconfig.read_text()
            if BLOCK in text:
                userconfig.write_text(text.replace(BLOCK, ''))
        if state.exists():
            try:
                previous = json.loads(state.read_text())
                if previous.get('cmdline_added'):
                    _remove_module_blacklist(root / 'boot/cmdline.txt')
            except (OSError, ValueError):
                pass
            state.unlink()
        print('Vinyltron-owned PWM settings removed. Reboot to apply audio changes. Legacy boot edits are preserved; see the install guide.')
        return
    conflict = audio_conflict(root)
    if not conflict and rule.exists() and rule.read_text() != RULE:
        conflict = 'Existing vinyltron-matrix.conf was modified; left unchanged. Review it before enabling hardware PWM.'
    cmdline = root / 'boot/cmdline.txt'
    if not conflict:
        try:
            _cmdline_tokens(cmdline)
        except (OSError, ValueError) as exc:
            conflict = 'Could not safely update /boot/cmdline.txt (%s). Hardware PWM protection was not installed.' % exc
    changed = False
    cmdline_added = False
    if not conflict:
        rule.parent.mkdir(parents=True, exist_ok=True)
        if not rule.exists():
            rule.write_text(RULE)
            rule.chmod(0o644)
            changed = True
        userconfig.parent.mkdir(parents=True, exist_ok=True)
        text = userconfig.read_text() if userconfig.exists() else ''
        if BLOCK not in text:
            userconfig.write_text(text + ('\n' if text and not text.endswith('\n') else '') + BLOCK)
            changed = True
        try:
            cmdline_added = _add_module_blacklist(cmdline)
            changed = changed or cmdline_added
        except (OSError, ValueError) as exc:
            conflict = 'Could not safely update /boot/cmdline.txt (%s). Some PWM settings may have been applied; review before rebooting.' % exc
    try:
        boot_id = (root / 'proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError:
        boot_id = ''
    if not changed and state.exists():
        try:
            previous = json.loads(state.read_text())
            changed = previous.get('changed', False) and previous.get('boot_id') == boot_id
            cmdline_added = previous.get('cmdline_added', False)
        except (OSError, ValueError):
            pass
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({'conflict': conflict, 'changed': changed, 'boot_id': boot_id,
                                 'cmdline_added': cmdline_added}))
    state.chmod(0o644)
    if conflict:
        print('WARNING: ' + conflict)
    else:
        print('Hardware PWM protection installed. The initramfs module load is blocked at the kernel command line. Onboard/HDMI audio is disabled; USB/I2S output remains available.')
        try:
            loaded = any(line.split()[0] == 'snd_bcm2835' for line in (root / 'proc/modules').read_text().splitlines() if line.split())
        except OSError:
            loaded = True
        if changed or loaded:
            print('REBOOT REQUIRED to apply hardware PWM protection. Use Volumio System > Restart; playback will stop.')
        print('Check PWM Status in Vinyltron Hardware settings after restart. No reboot is performed automatically.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('apply', 'remove'))
    parser.add_argument('--root', default='/', help='Filesystem root; tests use a temporary tree')
    args = parser.parse_args()
    setup(Path(args.root), remove=args.action == 'remove')
