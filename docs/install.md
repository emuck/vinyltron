# Install Guide

Vinyltron installs as a Volumio `user_interface` plugin. The normal path is the Volumio
web UI; no SSH is required for a standard install.

## Before You Install

Confirm the hardware basics first:

- Raspberry Pi running Volumio 4 / Bookworm
- 64x64 HUB75E RGB LED matrix
- Adafruit RGB Matrix Bonnet #3211, compatible HUB75 interface, or direct GPIO wiring
- Separate 5V high-current supply for the matrix
- Bonnet E-address jumper closed for 64-row panels, if using the Bonnet
- GPIO4-to-GPIO18 quality jumper installed if using Bonnet `adafruit-hat-pwm` quality mode

See [hardware setup](hardware.md) for wiring, power, and Bonnet details.

## Install From Volumio

1. Download the latest `vinyltron.zip` from
   [Releases](https://github.com/emuck/vinyltron/releases/latest).
2. Open the Volumio web UI.
3. Go to `Plugins -> Upload Plugin -> Manual Install`.
4. Upload `vinyltron.zip`.
5. Wait for Volumio to report that the plugin installed successfully.
6. Reboot if the installer says boot configuration changed.

The installer:

- Builds the pinned `rpi-rgb-led-matrix` C library and Python bindings on the Pi
- Installs Python dependencies used by the daemon and photo upload converter
- Installs the `vinyltron` systemd service
- Adds tightly scoped sudoers rules for controlling only the `vinyltron` service
- Configures boot files needed for matrix PWM

The matrix library build can take several minutes on a Pi 3B. See
[engineering-spec.md](engineering-spec.md#rpi-rgb-led-matrix-build) for build details.

## Boot Configuration

For Bonnet PWM mode, GPIO18/PWM must be free. Volumio's onboard/HDMI audio can claim that
PWM path, so Vinyltron's installer intentionally disables it:

- `/boot/userconfig.txt`: adds `dtparam=audio=off`
- `/boot/cmdline.txt`: removes Volumio's `snd_bcm2835.enable_hdmi=1` and
  `snd_bcm2835.enable_headphones=1` arguments
- `/boot/cmdline.txt`: adds `module_blacklist=snd_bcm2835` and
  `modprobe.blacklist=snd_bcm2835`

Before the first edit, the installer saves backups as:

- `/boot/cmdline.txt.vinyltron-orig`
- `/boot/userconfig.txt.vinyltron-orig`

Uninstalling the plugin does not revert these boot changes. Onboard/HDMI audio stays
disabled intentionally so GPIO18/PWM remains free for the matrix.

To restore onboard audio later, copy the backups back over the active boot files, if
present, then reboot:

```bash
sudo cp /boot/cmdline.txt.vinyltron-orig /boot/cmdline.txt
sudo cp /boot/userconfig.txt.vinyltron-orig /boot/userconfig.txt
sudo reboot
```

## First Settings Check

After install and reboot:

1. Open `Plugins -> User Interface -> Vinyltron`.
2. Confirm **Matrix Mapping** matches the hardware:
   - `Bonnet PWM` for the Adafruit Bonnet quality jumper path
   - `Bonnet` if the GPIO4-to-GPIO18 quality jumper is not installed
   - `Direct GPIO` if wiring the panel directly to the Pi
3. Confirm **Rotation** matches the mounted panel orientation.
4. Open the **Photo Manager** URL shown in the Idle Image settings from a device on the
   same network.

The photo manager defaults to:

```text
http://volumio.local:3018/photos
```

If port `3018` is unavailable, the Settings page shows an unavailable-port message. Change
**Photo Manager Port** to an unused port from `1024` to `65535` and save.

## Uninstall

Uninstall removes the plugin files, systemd service, sudoers entry, and runtime
configuration owned by the plugin. It intentionally leaves these behind:

- `/home/volumio/rpi-rgb-led-matrix`, because rebuilding it is slow and other matrix
  experiments may use it
- `/boot/*.vinyltron-orig` backups
- The active boot-file changes that keep onboard/HDMI audio disabled for matrix PWM

Use the restore commands above if you want to re-enable onboard/HDMI audio after removing
Vinyltron.
