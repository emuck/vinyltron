#!/bin/bash
# Deploy vinyltron source to Raspberry Pi
# Usage: ./deploy.sh [host]

PI_HOST=${1:-volumio.local}
PI_USER=volumio
PI_DIR=/home/volumio/vinyltron

echo "Deploying to ${PI_USER}@${PI_HOST}:${PI_DIR}..."

rsync -avz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='docs/' \
  --exclude='deploy.sh' \
  --exclude='*.md' \
  --exclude='rpi-rgb-led-matrix/' \
  ./ ${PI_USER}@${PI_HOST}:${PI_DIR}/

echo "Done. To run:"
echo "  ssh ${PI_USER}@${PI_HOST}"
echo "  cd ${PI_DIR} && sudo python3 vinyltron.py"
