#!/bin/bash
# Copy a built Vinyltron plugin zip to Volumio and install it through the Volumio CLI.
# Usage: ./tools/install-volumio-plugin-zip.sh [host] [zip]

set -e

PI_HOST=${1:-volumio.local}
ZIP_PATH=${2:-dist/vinyltron.zip}
PI_USER=volumio
REMOTE_ZIP=/tmp/vinyltron.zip
REMOTE_DIR=/tmp/vinyltron-plugin-install

if [ ! -f "$ZIP_PATH" ]; then
  echo "ERROR: plugin zip not found: $ZIP_PATH"
  echo "Build it first with ./tools/build-volumio-plugin.sh --with-node-modules"
  exit 1
fi

echo "Copying $ZIP_PATH to ${PI_USER}@${PI_HOST}:${REMOTE_ZIP}..."
scp "$ZIP_PATH" "${PI_USER}@${PI_HOST}:${REMOTE_ZIP}"

echo "Installing plugin on ${PI_HOST}..."
ssh -t "${PI_USER}@${PI_HOST}" "rm -rf ${REMOTE_DIR} && mkdir -p ${REMOTE_DIR} && unzip -q ${REMOTE_ZIP} -d ${REMOTE_DIR} && cd ${REMOTE_DIR} && if volumio plugin list 2>/dev/null | grep -q \"name: 'vinyltron'\"; then volumio plugin update; else volumio plugin install; fi && sudo systemctl restart vinyltron"

echo ""
echo "Done. Watch install/service logs with:"
echo "  ssh ${PI_USER}@${PI_HOST} 'journalctl -u volumio -f'"
echo "  ssh ${PI_USER}@${PI_HOST} 'journalctl -u vinyltron -f'"
