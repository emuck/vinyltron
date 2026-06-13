#!/bin/bash
# Called by Volumio when the plugin is uninstalled.
# User config and idle images are preserved under /data, as is the built
# rpi-rgb-led-matrix tree under /home/volumio. Boot config changes made by
# install.sh (/boot/userconfig.txt, /boot/cmdline.txt) are also left in place,
# since they only disable onboard audio/snd_bcm2835 and don't affect Volumio
# without the matrix daemon running.

/bin/systemctl stop vinyltron || true
/bin/systemctl disable vinyltron || true
rm -f /etc/systemd/system/vinyltron.service
rm -f /etc/sudoers.d/vinyltron
systemctl daemon-reload

echo "pluginuninstallend"
