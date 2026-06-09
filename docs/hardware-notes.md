# Hardware Notes

## Power check

Before testing through the Bonnet, clear the Pi's undervoltage indicator (lightning bolt).

The matrix 5V supply feeds the panel, not the Pi. With a Waveshare display attached the Pi
USB-C supply still needs to cover the Pi, display, and any USB devices.

1. Use a strong USB-C supply for the Pi — 5V 3A minimum for Pi 3B/4, official 27W for Pi 5
2. Use a separate 5V high-current supply for the matrix; observe polarity (5V to `+`, GND to `-`)
3. Seat the Bonnet fully on the 40-pin header — one row off in any direction causes problems
4. Make sure grounds are common (the Bonnet normally handles this through the GPIO header)
5. Don't tune anything while the lightning bolt is showing — undervoltage causes flicker,
   crashes, and corrupted SD writes that look like software bugs

```bash
vcgencmd get_throttled          # any non-zero value = Pi has seen throttling since boot
dmesg | grep -i voltage
```

## Hardware test sequence

Run this before starting vinyltron for the first time:

1. Boot with Pi power only — confirm no lightning bolt
2. Add the display — confirm still no lightning bolt
3. Add matrix 5V power — confirm still no lightning bolt
4. Confirm matrix power polarity before connecting the panel
5. Run a low-brightness demo first (see below)
6. Start vinyltron only after the demo is stable

## Blank matrix with Bonnet

The default config uses the Adafruit Bonnet quality/PWM wiring, which requires a jumper
wire between GPIO 4 and GPIO 18:

```toml
hardware_mapping = "adafruit-hat-pwm"
disable_hardware_pulsing = false
limit_refresh_rate_hz = 0
```

Without that jumper, use `hardware_mapping = "adafruit-hat"`. The plugin exposes both
settings under Hardware; changing them restarts the daemon because matrix geometry is set
during initialization.

Test the hardware independently before involving vinyltron:

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

1. Stop vinyltron first — two processes cannot share the GPIO
2. Check the HUB75 ribbon cable orientation
3. Check the panel power connector polarity
4. Confirm the Bonnet is not shifted on the GPIO header
5. Check that a Waveshare or other display is not occupying the same GPIO pins
6. If the panel is FM6126A-based, add `--led-panel-type=FM6126A`

`--led-limit-refresh=120` reduced horizontal static substantially on the tested panel.
It changed the symptom from TV-like snow to occasional flicker. Try values in the
90–140 range if the panel shows artifacts.
