# Vinyltron Next Steps

## Current Branch

Active branch: `volumio-plugin-work`

The current direction is to turn Vinyltron into a Volumio-owned plugin instead of a manually deployed daemon under `/home/volumio/vinyltron`.

## Current Volumio Plugin State

The dev install has been tested against:

- Volumio host: `192.168.88.50`
- Plugin path: `/data/plugins/user_interface/vinyltron`
- Daemon runtime path: `/data/plugins/user_interface/vinyltron/vinyltron`
- Persistent config path: `/data/configuration/user_interface/vinyltron/config.toml`
- Systemd service: `vinyltron.service`

The service should run the daemon with:

```text
/usr/bin/python3 /data/plugins/user_interface/vinyltron/vinyltron/vinyltron.py /data/configuration/user_interface/vinyltron/config.toml
```

## Bonnet And Power Check

Before testing the LED matrix through the bonnet, resolve the Raspberry Pi lightning bolt indicator.

The lightning bolt means the Pi is seeing undervoltage. The separate 5V matrix supply connected to the bonnet usually powers the LED matrix side, not necessarily the Pi itself. With the Waveshare 5-inch display attached, the Pi USB-C supply still needs enough current for the Pi, display, USB devices, and any attached accessories.

Checklist:

1. Use a strong USB-C supply for the Pi itself.
   - For Raspberry Pi 5, use the official 27W USB-C supply or equivalent.
   - For Raspberry Pi 4, use a reliable 5V 3A USB-C supply.
2. Use a separate 5V high-current supply for the RGB matrix/bonnet.
   - Observe polarity carefully: 5V to `+`, ground to `-`.
   - Do not power a large matrix from the Pi 5V GPIO pins.
3. Make sure the bonnet is seated on the GPIO header correctly.
   - It should cover the full 40-pin header.
   - It must not be shifted left/right or up/down by one row.
4. Make sure grounds are common.
   - A proper matrix bonnet normally handles this through the GPIO header plus the matrix power input.
5. Do not continue LED stress testing while the lightning bolt is present.
   - Undervoltage can cause flicker, crashes, corrupted SD writes, USB disconnects, or misleading display behavior.

Useful Volumio commands:

```bash
vcgencmd get_throttled
dmesg | grep -i voltage
journalctl -k | grep -i voltage
```

For `vcgencmd get_throttled`, any non-zero value means the Pi has seen throttling or undervoltage since boot.

## Immediate Hardware Test Sequence

After the lightning bolt is gone:

1. Boot with Pi USB-C power only and confirm there is no lightning bolt.
2. Add the Waveshare display and confirm there is still no lightning bolt.
3. Add bonnet/matrix 5V power and confirm there is still no lightning bolt.
4. Confirm the matrix power polarity before connecting the panel.
5. Run a low-brightness matrix test first.
6. Start Vinyltron only after the hardware test is stable.

## Blank Matrix With Bonnet

The current code defaults to the Adafruit RGB Matrix Bonnet quality/PWM wiring:

```python
opts.hardware_mapping = d.get('hardware_mapping', 'adafruit-hat-pwm')
opts.disable_hardware_pulsing = d.get('disable_hardware_pulsing', False)
```

The config keys are:

```toml
hardware_mapping = "adafruit-hat-pwm"
disable_hardware_pulsing = false
limit_refresh_rate_hz = 0
```

This requires the bonnet quality jumper wire between `GPIO4` and `GPIO18`. Without that wire, use `hardware_mapping = "adafruit-hat"`. `limit_refresh_rate_hz = 0` leaves the matrix driver uncapped; use values around `90-140` if a panel shows flicker or refresh hiccups.

Do not tune this while the Pi is showing the lightning bolt. First get power stable, then test the matrix with the `rpi-rgb-led-matrix` demo using the bonnet mapping:

```bash
cd ~/rpi-rgb-led-matrix
sudo examples-api-use/demo \
  --led-rows=64 --led-cols=64 \
  --led-gpio-mapping=adafruit-hat-pwm \
  --led-slowdown-gpio=2 \
  --led-limit-refresh=120 \
  --led-brightness=20
```

If the panel is still blank:

1. Stop `vinyltron` before running demos so two processes do not fight for GPIO.
2. Confirm the HUB75 ribbon cable orientation.
3. Confirm the panel power connector is seated and polarity is correct.
4. Confirm the bonnet is not shifted by one row or column on the Pi GPIO header.
5. Confirm the Waveshare display is not occupying or blocking the same GPIO pins.
6. Try `--led-slowdown-gpio=4` as a comparison only; on this panel it caused more horizontal flicker.
7. If the panel is FM6126A-based, add `--led-panel-type=FM6126A`.

Current bonnet finding: `--led-limit-refresh=120` reduced the horizontal static substantially. It did not eliminate every flicker artifact, but it changed the symptom from TV-like snow to occasional flicker.

Once the demo works through the bonnet, deploy the plugin again and restart `vinyltron`. If reverting to bonnet wiring without the quality jumper, set `hardware_mapping = "adafruit-hat"`. If reverting to direct GPIO wiring later, set `hardware_mapping = "regular"` and `disable_hardware_pulsing = true`.

The Volumio plugin exposes Matrix Mapping and Refresh Limit under Hardware. Refresh Limit accepts any nonnegative integer; `0` means uncapped. Saving these settings restarts `vinyltron` because the RGB matrix options are only applied during matrix initialization.

## Plugin Work Still To Do

1. Confirm the plugin appears and can be enabled/disabled from Volumio's plugin UI.
2. Confirm settings changes in the Volumio UI update `/data/configuration/user_interface/vinyltron/config.toml`.
3. Confirm `vinyltron.service` restarts or reloads cleanly after settings changes.
4. Build a release zip with `tools/build-volumio-plugin.sh`.
5. Test installing from the zip on a clean Volumio image or clean plugin uninstall/reinstall.
6. Decide whether legacy `/home/volumio/vinyltron` migration should remain permanent or become a one-time compatibility path.

## Known Follow-Ups

- Make the plugin install flow less dependent on dev SSH helpers.
- Add a clear plugin status display for daemon active/inactive.
- Add basic validation for config fields before writing TOML.
- Keep microphone recognition and microphone visualizer experiments on separate branches until they are product-ready.
- Keep the idle image / picture-frame behavior in scope as a useful non-playing mode.

## Idle Photo Frame

When Idle Mode is `Random Folder Image`, Vinyltron can rotate through images in the idle folder while Volumio remains stopped/idle. The plugin exposes `Photo Interval (seconds)` in the Idle Image section:

- `0` disables timed rotation.
- `300` changes the photo every five minutes.
- Rotation stops as soon as Volumio starts playing or paused album art is shown.

Use `tools/convert-idle-images.py` to pre-convert normal photos into 64x64 optimized PNGs before copying them into `/data/INTERNAL/Vinyltron/idle-images`:

```bash
python3 tools/convert-idle-images.py ~/Pictures/vinyltron /tmp/vinyltron-idle --recursive
```

The converter applies EXIF orientation, center-crops to square, resizes with LANCZOS, and writes lossless PNG output.

HEIC/HEIF iPhone photos are accepted. If Pillow cannot open them directly, the converter falls back to macOS `sips` automatically.
