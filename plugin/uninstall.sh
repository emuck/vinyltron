#!/bin/bash
# Called by Volumio when the plugin is uninstalled.
# Python daemon files in /home/volumio/vinyltron/ are left in place.

/bin/systemctl stop vinyltron || true
/bin/systemctl disable vinyltron || true
rm -f /etc/systemd/system/vinyltron.service
rm -f /etc/sudoers.d/vinyltron
systemctl daemon-reload

echo "pluginuninstallend"
