#!/bin/bash
# Called by Volumio when the plugin is uninstalled.
# User settings/photos and legacy boot edits are preserved. Remove only our
# exact module rule and marked boot block, never overwrite later user edits.

/bin/systemctl stop vinyltron || true
/bin/systemctl disable vinyltron || true
PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$PLUGIN_DIR/vinyltron/pwm_setup.py" remove || echo "WARNING: PWM cleanup failed; see install guide."
rm -f /run/vinyltron/pwm.json
rm -f /etc/systemd/system/vinyltron.service
rm -f /etc/sudoers.d/vinyltron
systemctl daemon-reload

echo "pluginuninstallend"
