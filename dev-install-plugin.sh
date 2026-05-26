#!/bin/bash
# Dev-install the Vinyltron Volumio plugin
# Run from projects/vinyltron/
# Usage: ./dev-install-plugin.sh [host]

set -e

PI_HOST=${1:-volumio.local}
PI_USER=volumio
PLUGIN_DIR=/data/plugins/user_interface/vinyltron

echo "=== Vinyltron plugin dev-install ==="
echo "Target: ${PI_USER}@${PI_HOST}"

# Sync plugin files — node_modules built on Pi, not synced from Mac
echo "Syncing plugin files..."
rsync -avz --exclude='node_modules' \
  ./plugin/ ${PI_USER}@${PI_HOST}:${PLUGIN_DIR}/

# All remaining setup runs on the Pi
ssh -T ${PI_USER}@${PI_HOST} bash -s << 'ENDSSH'
set -e
PLUGIN_DIR=/data/plugins/user_interface/vinyltron

echo "Running npm install..."
cd "${PLUGIN_DIR}"
npm install --silent

echo "Registering in plugins.json..."
python3 -c "
import json
p = '/data/plugins/plugins.json'
try:
    d = json.load(open(p))
except Exception:
    d = {}
d.setdefault('user_interface', {})['vinyltron'] = {'enabled': True, 'status': 'STARTED'}
open(p, 'w').write(json.dumps(d, indent=4))
print('Registered.')
"

echo "Running plugin install.sh..."
sudo bash "${PLUGIN_DIR}/install.sh"

echo "Restarting Volumio to load plugin..."
sudo systemctl restart volumio
ENDSSH

echo ""
echo "Done. Wait ~30s for Volumio to restart, then check:"
echo "  Settings → Plugins → User Interface → Vinyltron"
