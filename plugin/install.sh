#!/bin/bash
# Called by Volumio after plugin zip is extracted.
# Assumes vinyltron Python daemon is already deployed to /home/volumio/vinyltron/

set -e

VINYLTRON_DIR=/home/volumio/vinyltron
SERVICE=vinyltron
IDLE_IMAGE_DIR=/data/INTERNAL/Vinyltron/idle-images

echo "Creating idle image folder..."
mkdir -p "$IDLE_IMAGE_DIR"
chown -R volumio:volumio /data/INTERNAL/Vinyltron

# Install Python dependencies
if [ -f "$VINYLTRON_DIR/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip3 install -r "$VINYLTRON_DIR/requirements.txt"
fi

# Install and enable systemd service
if [ -f "$VINYLTRON_DIR/vinyltron.service" ]; then
    echo "Installing systemd service..."
    cp "$VINYLTRON_DIR/vinyltron.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable $SERVICE
fi

# Allow volumio user to control the service without a password
cat > /etc/sudoers.d/vinyltron <<'EOF'
volumio ALL=(ALL) NOPASSWD: /bin/systemctl start vinyltron, /bin/systemctl stop vinyltron, /bin/systemctl restart vinyltron, /bin/systemctl reload vinyltron
EOF
chmod 440 /etc/sudoers.d/vinyltron

echo "plugininstallend"
