"""Report effective driver mode only after matrix construction succeeds."""
import json
import os
from pathlib import Path

STATUS_PATH = Path('/run/vinyltron/pwm.json')


def write_pwm_status(mode, reason):
    try:
        boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        # Reject stale status even if the PID is reused after a service restart.
        start_ticks = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
        data = {'pid': os.getpid(), 'boot_id': boot_id, 'start_ticks': start_ticks,
                'mode': mode, 'reason': reason}
        temporary = STATUS_PATH.with_suffix('.tmp')
        with temporary.open('w') as stream:
            os.fchmod(stream.fileno(), 0o644)
            json.dump(data, stream)
        temporary.replace(STATUS_PATH)
    except (OSError, ValueError, IndexError):
        # A diagnostic file must never prevent display operation.
        pass
