# Hardware Setup

Vinyltron runs with a Raspberry Pi and a 64x64 HUB75E matrix. The Adafruit RGB Matrix
Bonnet is recommended, but it is not strictly required. The important constraints are
power, level shifting, row addressing, and GPIO18/PWM ownership.

## Tested Bill Of Materials

| # | Item | Notes | Approx. price |
|---|---|---|---|
| 1 | 64x64 RGB LED Matrix, P3, 192x192mm, HUB75E | 1/32 scan, 5V/4A panel | $37 |
| 2 | Adafruit RGB Matrix Bonnet for Raspberry Pi #3211 | Recommended level shifting and HUB75 connector | $15 |
| 3 | 5V 4A switching PSU | Matrix rail only | $12-15 |

IDC ribbon cable and panel power cable are usually included with the matrix.

## Raspberry Pi

The primary tested platform is Raspberry Pi 3B running Volumio 4 / Bookworm.

Pi 5 status:

- The plugin installs on Pi 5.
- The daemon starts and shuts down cleanly in software-pulse mode.
- Hardware-pulse mode is forced off on Pi 5 because the pinned matrix library predates RP1
  GPIO support.
- Actual HUB75 panel rendering on Pi 5 remains untested.

## Matrix Panel

Tested panel:

- 64x64 RGB LED matrix
- P3 pitch
- HUB75E, 5-bit row addressing
- 1/32 scan
- 5V input, up to about 4A at full white

The tested Seengreat/Amazon panel behaves correctly with the default matrix settings. Some
FM6126A-based panels may require `panel_type = "FM6126A"` in `config.toml` or
`--led-panel-type=FM6126A` when running matrix library demos directly.

## Interface Options

Vinyltron was originally developed with direct GPIO wiring. That works, and the occasional
flicker can even read as a pleasing retro display effect. Use it if that is the look you
want or if you are experimenting.

For a cleaner and more stable matrix, use the Adafruit Bonnet. The Bonnet level-shifts Pi
GPIO from 3.3V to the 5V logic expected by HUB75 panels and gives the panel a proper HUB75
connector.

## Bonnet Requirements

For Bonnet wiring:

Required:

- Close the Bonnet's E-address solder jumper for 64-row HUB75E panels.
- Install the GPIO4-to-GPIO18 quality jumper for `adafruit-hat-pwm` quality mode.
- Use `Matrix Mapping = Bonnet PWM` in the plugin when that jumper is installed.

Without the GPIO4-to-GPIO18 quality jumper, use `Matrix Mapping = Bonnet`.

For direct GPIO wiring, use `Matrix Mapping = Direct GPIO`. Expect more flicker and less
signal margin than the Bonnet path.

## Power

Use separate power supplies:

- Pi power supply for the Pi, touchscreen, and USB devices
- 5V high-current matrix supply for the panel

Do not power the matrix from the Pi. The matrix supply feeds the panel through the Bonnet's
barrel jack input. Check polarity before connecting the panel.

Before tuning software, clear any Pi undervoltage warnings. Undervoltage causes flicker,
crashes, and SD-card problems that look like software bugs.

Useful checks on the Pi:

```bash
vcgencmd get_throttled
dmesg | grep -i voltage
```

Any non-zero `vcgencmd get_throttled` value means the Pi has seen throttling since boot.

## First Hardware Bring-Up

1. Boot with Pi power only and confirm there is no undervoltage warning.
2. Add any touchscreen or USB devices and confirm power is still stable.
3. Connect matrix 5V power with correct polarity.
4. Seat the Bonnet fully on the 40-pin header.
5. Connect the HUB75 ribbon cable with correct orientation.
6. Start with low brightness.

If you test the matrix library directly, stop Vinyltron first. Two processes cannot share
the GPIO matrix output.

```bash
cd ~/rpi-rgb-led-matrix
sudo examples-api-use/demo \
  --led-rows=64 --led-cols=64 \
  --led-gpio-mapping=adafruit-hat-pwm \
  --led-slowdown-gpio=2 \
  --led-limit-refresh=120 \
  --led-brightness=20
```

`--led-limit-refresh=120` reduced horizontal static on the tested panel. Values in the
90-140 range are useful if the panel shows artifacts.

## Waveshare DSI Touch Display

The tested Waveshare 5-inch capacitive touch display is the DSI variant and does not
conflict with the Bonnet GPIO pins. DSI uses the dedicated MIPI DSI connector; touch I2C
on GPIO 2/3 does not conflict with the matrix output path.
