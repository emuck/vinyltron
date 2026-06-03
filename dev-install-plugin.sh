#!/bin/bash
# Dev-install the Vinyltron Volumio plugin
# Run from projects/vinyltron/
# Usage: ./dev-install-plugin.sh [host]

set -e

PI_HOST=${1:-volumio.local}
PI_USER=volumio
PLUGIN_DIR=/data/plugins/user_interface/vinyltron
DAEMON_DIR=${PLUGIN_DIR}/vinyltron

echo "=== Vinyltron plugin dev-install ==="
echo "Target: ${PI_USER}@${PI_HOST}"

if ! ssh -o ConnectTimeout=5 ${PI_USER}@${PI_HOST} true; then
  echo "ERROR: cannot SSH to ${PI_USER}@${PI_HOST}"
  echo "Pass the Pi IP or reachable hostname, for example: ./dev-install-plugin.sh 192.168.1.42"
  exit 1
fi

# Sync plugin files — node_modules built on Pi, not synced from Mac
echo "Syncing plugin files..."
rsync -avz --exclude='node_modules' \
  ./plugin/ ${PI_USER}@${PI_HOST}:${PLUGIN_DIR}/

echo "Syncing daemon runtime files..."
ssh -T ${PI_USER}@${PI_HOST} "mkdir -p ${DAEMON_DIR}"
rsync -avz --delete --delete-excluded \
  --filter='protect __pycache__/***' \
  --filter='hide __pycache__/***' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='.git/' \
  --exclude='.gitignore' \
  --exclude='dist/' \
  --exclude='docs/' \
  --exclude='rpi-rgb-led-matrix/' \
  --exclude='deploy.sh' \
  --exclude='dev-install-plugin.sh' \
  --exclude='install.sh' \
  --exclude='plugin/' \
  --exclude='test_matrix.py' \
  --exclude='tools/' \
  --exclude='vinyltron.service' \
  --exclude='*.md' \
  ./ ${PI_USER}@${PI_HOST}:${DAEMON_DIR}/

# Non-sudo: npm install + register in plugins.json (no TTY needed)
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
ENDSSH

# Sudo steps: plugin install.sh + Volumio restart (TTY required for sudo)
echo "Running plugin install.sh and restarting Volumio (may prompt for sudo password)..."
if [ -n "${VINYLTRON_DEV_SUDO_PASSWORD:-}" ]; then
  ssh -T ${PI_USER}@${PI_HOST} "sudo -S -p '' bash ${PLUGIN_DIR}/install.sh && (sudo -S -p '' systemctl restart volumio || true)" << ENDSSH
${VINYLTRON_DEV_SUDO_PASSWORD}
${VINYLTRON_DEV_SUDO_PASSWORD}
ENDSSH
else
  ssh -t ${PI_USER}@${PI_HOST} "sudo bash ${PLUGIN_DIR}/install.sh && (sudo systemctl restart volumio || true)"
fi

echo ""
echo "Done. Wait ~30s for Volumio to restart, then check:"
echo "  Settings → Plugins → User Interface → Vinyltron"
