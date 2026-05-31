#!/bin/bash
# Build a Volumio-compatible Vinyltron plugin zip.
# The zip root contains plugin files; the Python daemon is bundled in ./vinyltron/.

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_DIR="$ROOT_DIR/plugin"
DIST_DIR="$ROOT_DIR/dist"
STAGE_DIR="$DIST_DIR/vinyltron-plugin"
ZIP_PATH="$DIST_DIR/vinyltron.zip"

echo "Building Vinyltron plugin package..."
rm -rf "$STAGE_DIR" "$ZIP_PATH"
mkdir -p "$STAGE_DIR/vinyltron" "$DIST_DIR"

echo "Copying plugin files..."
rsync -av \
  --exclude='node_modules' \
  "$PLUGIN_DIR"/ "$STAGE_DIR"/

echo "Copying daemon runtime..."
rsync -av \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='docs/' \
  --exclude='rpi-rgb-led-matrix/' \
  --exclude='deploy.sh' \
  --exclude='dev-install-plugin.sh' \
  --exclude='install.sh' \
  --exclude='plugin/' \
  --exclude='tools/' \
  --exclude='dist/' \
  --exclude='*.md' \
  "$ROOT_DIR"/ "$STAGE_DIR/vinyltron"/

echo "Installing Node dependencies into package..."
cd "$STAGE_DIR"
npm install --production --silent

echo "Creating $ZIP_PATH..."
zip -qr "$ZIP_PATH" .

echo "Done: $ZIP_PATH"
