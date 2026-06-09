#!/bin/bash
# Build a Volumio-compatible Vinyltron plugin zip.
# The zip root contains plugin files; the Python daemon is bundled in ./vinyltron/.
# Usage: ./tools/build-volumio-plugin.sh [--with-node-modules]

set -e

WITH_NODE_MODULES=false
if [ "${1:-}" = "--with-node-modules" ]; then
  WITH_NODE_MODULES=true
fi

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
  --exclude='.git/' \
  --exclude='.claude/' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='.gitignore' \
  --exclude='docs/' \
  --exclude='rpi-rgb-led-matrix/' \
  --exclude='deploy.sh' \
  --exclude='dev-install-plugin.sh' \
  --exclude='install.sh' \
  --exclude='plugin/' \
  --exclude='tools/' \
  --exclude='dist/' \
  --exclude='*.md' \
  --exclude='test_matrix.py' \
  --exclude='vinyltron.service' \
  "$ROOT_DIR"/ "$STAGE_DIR/vinyltron"/

cd "$STAGE_DIR"
if [ "$WITH_NODE_MODULES" = true ]; then
  echo "Installing Node dependencies into package..."
  npm install --production --silent
else
  echo "Skipping node_modules. Use --with-node-modules for a release-style package."
fi

echo "Creating $ZIP_PATH..."
zip -qr "$ZIP_PATH" .

echo "Done: $ZIP_PATH"
