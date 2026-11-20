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
- SSH access to the Pi (enabled in Volumio under `Settings -> System`) — required for
  the ZIP install path and post-install troubleshooting; not needed for the plugin store path

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
claim that PWM path. Use a USB DAC or I2S output. The installer checks the selected
Volumio audio card before changing audio/boot settings. If onboard/HDMI audio is
selected, or the output cannot be verified, it leaves those settings alone and shows
an audio-conflict warning. Select USB/I2S audio, then reinstall/update Vinyltron.

For a verified compatible output, the installer adds:

- `/etc/modprobe.d/vinyltron-matrix.conf`: `blacklist snd_bcm2835` and
  `install snd_bcm2835 /bin/false`, blocking ordinary automatic and explicit modprobe
  loads after the real root filesystem mounts.
- A marked `[all]` / `dtparam=audio=off` block in `/boot/userconfig.txt`.
- `module_blacklist=snd_bcm2835` in `/boot/cmdline.txt`. This kernel-level setting is
  needed because Volumio's initramfs explicitly loads `snd-bcm2835` before those rootfs
  modprobe rules are available. Vinyltron rechecks it at service start to repair a
  regenerated command line for the next reboot.

It never unloads a live audio driver or reboots automatically. When prompted, reboot
through Volumio's System settings. Then refresh Vinyltron settings and inspect
**Hardware → PWM Status**: it reports the running driver's actual hardware/software
mode, an audio conflict, reboot guidance, or a waiting state if the display has not
initialized yet. The saved hardware mapping alone does not confirm hardware PWM.

Older installations edited `/boot/cmdline.txt` and saved `.vinyltron-orig` backups.
The installer records whether it added the kernel blacklist and removes only its own
`snd_bcm2835` entry on uninstall, preserving other blacklist entries. Legacy command-line
edits are preserved because their ownership cannot be determined safely. To restore
onboard audio after uninstalling an older version, review and remove legacy
`dtparam=audio=off` and `snd_bcm2835` blacklist arguments, then reboot. Compare old
backups if available; do not blindly overwrite later boot configuration changes.

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

Uninstall removes the service, sudoers entry, runtime PWM status, the exact plugin-owned
module rule, and its marked boot block. Modified rules and unrelated boot settings are
preserved. User config/photos remain under `/data`. Reboot after uninstall to apply
audio changes. Older boot edits/backups remain; see Boot Configuration above.
