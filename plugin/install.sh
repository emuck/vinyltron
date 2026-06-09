#!/bin/bash
# Called by Volumio after plugin zip is extracted.

set -e

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
VINYLTRON_DIR="$PLUGIN_DIR/vinyltron"
LEGACY_DIR=/home/volumio/vinyltron
CONFIG_DIR=/data/configuration/user_interface/vinyltron
CONFIG_TOML="$CONFIG_DIR/config.toml"
SERVICE=vinyltron
IDLE_IMAGE_DIR=/data/INTERNAL/Vinyltron/idle-images

if [ ! -f "$VINYLTRON_DIR/vinyltron.py" ]; then
    echo "ERROR: bundled Vinyltron daemon not found at $VINYLTRON_DIR"
    exit 1
fi

MATRIX_LIB=/home/volumio/rpi-rgb-led-matrix/bindings/python
if ! python3 -c "import sys; sys.path.insert(0, '$MATRIX_LIB'); import rgbmatrix" 2>/dev/null; then
    echo "ERROR: rpi-rgb-led-matrix Python bindings not found at $MATRIX_LIB"
    echo "Build the library before installing — see https://github.com/emuck/vinyltron#prerequisites"
    exit 1
fi

echo "Creating idle image folder..."
mkdir -p "$IDLE_IMAGE_DIR"
chown -R volumio:volumio /data/INTERNAL/Vinyltron

echo "Preparing Vinyltron configuration..."
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_TOML" ]; then
    if [ -f "$LEGACY_DIR/config.toml" ]; then
        echo "Migrating existing config.toml from $LEGACY_DIR"
        cp "$LEGACY_DIR/config.toml" "$CONFIG_TOML"
    else
        cp "$VINYLTRON_DIR/config.toml" "$CONFIG_TOML"
    fi
fi
chown -R volumio:volumio "$CONFIG_DIR"

# Install Python dependencies
if [ -f "$VINYLTRON_DIR/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    # --break-system-packages required on Python 3.11+ (PEP 668 / Bookworm)
    PIP_FLAGS=""
    python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null && PIP_FLAGS="--break-system-packages"
    pip3 install $PIP_FLAGS -r "$VINYLTRON_DIR/requirements.txt"
fi

# Install and enable systemd service
echo "Installing systemd service..."
cat > /etc/systemd/system/vinyltron.service <<EOF
[Unit]
Description=Vinyltron — HUB75 album art display
After=network.target volumio.service
Wants=volumio.service

[Service]
Type=simple
WorkingDirectory=$VINYLTRON_DIR
ExecStart=/usr/bin/python3 $VINYLTRON_DIR/vinyltron.py $CONFIG_TOML
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable $SERVICE

# Allow volumio user to control the service without a password
cat > /etc/sudoers.d/vinyltron <<'EOF'
volumio ALL=(ALL) NOPASSWD: /bin/systemctl start vinyltron, /bin/systemctl stop vinyltron, /bin/systemctl restart vinyltron, /bin/systemctl reload vinyltron, /bin/systemctl is-active vinyltron
EOF
chmod 440 /etc/sudoers.d/vinyltron

echo "plugininstallend"
