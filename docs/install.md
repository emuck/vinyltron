# Install Guide

Vinyltron installs as a Volumio `user_interface` plugin, available in the
Volumio plugin store on the **beta channel**.

## Before You Install

Confirm the hardware basics first:

- Raspberry Pi running Volumio 4 / Bookworm
- 64×64 HUB75E RGB LED matrix
- Adafruit RGB Matrix Bonnet #3211, compatible HUB75 interface, or direct GPIO wiring
- Separate 5V high-current supply for the matrix
- Bonnet E-address jumper closed for 64-row panels, if using the Bonnet
- GPIO4-to-GPIO18 quality jumper installed if using Bonnet `adafruit-hat-pwm` quality mode
- SSH access to the Pi (enabled in Volumio under `Settings -> System`)

See [hardware setup](hardware.md) for wiring, power, and Bonnet details.

## Install from the Plugin Store (recommended)

1. Open the Volumio web UI and go to **Plugins → User Interface**.
2. Find **Vinyltron** and click **Install**.
3. Wait for the install to complete, then reboot if prompted (the installer
   configures boot files for matrix PWM — a reboot is required for those to
   take effect).

The installer:

- Installs Python dependencies used by the daemon and photo upload converter
- Installs prebuilt `rgbmatrix` bindings (no compilation required)
- Adds Bookworm backports and installs `libheif-examples` when available, so
  iPhone HEIC/HEIF photo uploads can be decoded by `heif-convert`
- Installs the `vinyltron` systemd service
- Adds tightly scoped sudoers rules for controlling only the `vinyltron` service
- Configures boot files needed for matrix PWM

## Install from a Release Zip (advanced / development)

If the store is unavailable or you need a specific build:

1. Download the latest `vinyltron.zip` from
   [Releases](https://github.com/emuck/vinyltron/releases/latest).
2. Copy it to the Pi and install:

   ```bash
   scp vinyltron.zip volumio@volumio.local:/tmp/
   ssh volumio@volumio.local
   rm -rf /tmp/vinyltron-install && mkdir /tmp/vinyltron-install
   unzip -q /tmp/vinyltron.zip -d /tmp/vinyltron-install
   cd /tmp/vinyltron-install && volumio plugin install
   ```

   `volumio plugin install` shows an unverified-plugin warning and asks
   `Do you want to install this plugin anyway?` — answer `y`. If Vinyltron is
   already installed, use `volumio plugin update` instead; `install` fails with
   `Plugin vinyltron already exists` on an existing install.

   After an update, restart both services to pick up the new code:

   ```bash
   sudo systemctl restart volumio
   sudo systemctl restart vinyltron
   ```

3. Wait for `plugininstallend` in the output.
4. Reboot if the install output says boot configuration changed.

If you have this repo cloned, `./tools/install-volumio-plugin-zip.sh [host] [zip]`
does steps 2–3 automatically, choosing `install` or `update` based on whether
Vinyltron is already installed.

## Boot Configuration

For Bonnet PWM mode, GPIO18/PWM must be free. Volumio's onboard/HDMI audio can
claim that PWM path, so Vinyltron's installer intentionally disables it:

- `/boot/userconfig.txt`: adds `dtparam=audio=off`
- `/boot/cmdline.txt`: removes Volumio's `snd_bcm2835.enable_hdmi=1` and
  `snd_bcm2835.enable_headphones=1` arguments
- `/boot/cmdline.txt`: adds `module_blacklist=snd_bcm2835` and
  `modprobe.blacklist=snd_bcm2835`

Before the first edit, the installer saves backups as:

- `/boot/cmdline.txt.vinyltron-orig`
- `/boot/userconfig.txt.vinyltron-orig`

Uninstalling the plugin does not revert these boot changes. Onboard/HDMI audio
stays disabled intentionally so GPIO18/PWM remains free for the matrix.

To restore onboard audio later, copy the backups back over the active boot
files, if present, then reboot:

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
4. Open the **Photo Manager** URL shown in the Idle Image settings from a
   device on the same network.

The photo manager defaults to:

```text
http://volumio.local:3018/photos
```

If port `3018` is unavailable, the Settings page shows an unavailable-port
message. Change **Photo Manager Port** to an unused port from `1024` to
`65535` and save.

## Uninstall

Uninstall removes the plugin files, systemd service, sudoers entry, and
runtime configuration owned by the plugin. It intentionally leaves:

- `/boot/*.vinyltron-orig` backups
- The active boot-file changes that keep onboard/HDMI audio disabled for
  matrix PWM

Use the restore commands above if you want to re-enable onboard/HDMI audio
after removing Vinyltron.
