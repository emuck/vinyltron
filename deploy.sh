#!/bin/bash
# Deploy vinyltron source to Raspberry Pi
# Usage: ./deploy.sh [--with-config] [host]

set -e

SYNC_CONFIG=false
if [ "$1" = "--with-config" ]; then
  SYNC_CONFIG=true
  shift
fi

PI_HOST=${1:-volumio.local}
PI_USER=volumio
PI_DIR=/home/volumio/vinyltron
CONFIG_EXCLUDE=("--exclude=config.toml")

if [ "$SYNC_CONFIG" = true ]; then
  CONFIG_EXCLUDE=()
fi

echo "Deploying to ${PI_USER}@${PI_HOST}:${PI_DIR}..."
if [ "$SYNC_CONFIG" = true ]; then
  echo "Including config.toml"
else
  echo "Preserving remote config.toml (use --with-config to overwrite)"
fi

rsync -avz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  "${CONFIG_EXCLUDE[@]}" \
  --exclude='docs/' \
  --exclude='deploy.sh' \
  --exclude='*.md' \
  --exclude='rpi-rgb-led-matrix/' \
  ./ ${PI_USER}@${PI_HOST}:${PI_DIR}/

echo "Done. To run:"
echo "  ssh ${PI_USER}@${PI_HOST}"
echo "  cd ${PI_DIR} && sudo python3 vinyltron.py"
