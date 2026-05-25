#!/bin/bash
# Install vinyltron on Volumio / Raspberry Pi
# Run once after deploy: sudo bash install.sh

set -e

INSTALL_DIR=/home/volumio/vinyltron
SERVICE=vinyltron.service
MATRIX_DIR=/home/volumio/rpi-rgb-led-matrix

echo "=== Vinyltron installer ==="

# Verify rpi-rgb-led-matrix library is built
if [ ! -d "$MATRIX_DIR/bindings/python/rgbmatrix" ]; then
    echo "ERROR: rpi-rgb-led-matrix Python bindings not found at $MATRIX_DIR"
    echo "Build them first — see docs/engineering-spec.md"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt"

# Install and enable systemd service
echo "Installing systemd service..."
cp "$INSTALL_DIR/$SERVICE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"

echo ""
echo "Done. To start now:  systemctl start $SERVICE"
echo "      To view logs:  journalctl -u $SERVICE -f"
