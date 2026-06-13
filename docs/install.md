# Install

Download the latest `vinyltron.zip` from [Releases](../../../releases), then in Volumio:
**Settings → Plugins → Manual Install → select the zip.**

The installer builds the rpi-rgb-led-matrix C library and Python bindings from source for
the Pi it's running on (first install only — roughly 25 minutes on a Pi 3B), bundles the
Python daemon, installs a systemd service, sets up the sudoers rules needed for service
control, and configures the boot files needed for matrix PWM (see "Boot configuration"
below). No SSH required — but a reboot may be needed afterwards for the boot config
changes to take effect.

The bundled `tools/matrix-build/` helpers (`setup.py` and an `Imaging.h` stub) are custom
build helpers needed because the pinned library commit predates `pyproject.toml` — see
[engineering-spec.md](engineering-spec.md#rpi-rgb-led-matrix-build) for details.

## Boot configuration

`install.sh` automatically disables onboard audio (`dtparam=audio=off` in
`/boot/userconfig.txt`) and blacklists `snd_bcm2835` (`/boot/cmdline.txt`) so GPIO 18 is
free for matrix PWM and `adafruit-hat-pwm` hardware pulsing works — no SSH required. If
either file needed changes, the installer prints a message asking you to **reboot the
Pi** afterwards. The originals are saved as `cmdline.txt.vinyltron-orig` and
`userconfig.txt.vinyltron-orig`. Uninstalling the plugin does not revert these boot
config changes, since they only disable onboard audio/`snd_bcm2835` and have no effect
without the matrix daemon running.

After rebooting, `grep '^snd_bcm2835 ' /proc/modules` should return no output.

## Manual hardware steps

Two things `install.sh` can't do for you:

- Close the HUB75E E-address solder jumper on the Bonnet for 64-row support
- `slowdown_gpio = 2` in `config.toml` (the default)
