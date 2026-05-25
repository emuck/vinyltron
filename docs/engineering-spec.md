# Engineering Spec

## System Overview

Voluma is a Linux daemon running on a Raspberry Pi 3B alongside Volumio 3.x. It subscribes
to Volumio's Socket.io `pushState` event stream for real-time track change notifications,
fetches album art, processes it through an image pipeline, and pushes frames to a 64×64
HUB75E RGB LED matrix via the rpi-rgb-led-matrix C library.

## Hardware Constraints

### Raspberry Pi 3B
- GPIO: 3.3V logic — direct HUB75E connection runs but causes **vertical column flicker**
  (confirmed 2026-05-23). Root cause: Pi 3B GPIO (3.3V) is below the 5V CMOS VIH threshold
  (0.7×5V = 3.5V) of the panel's row driver ICs. Not software-tunable.
  **Adafruit Bonnet (#3211)** with 74AHCT245 level shifters (VIH ~2.0V) is the definitive fix — on order.
- GPIO speed: `opts.gpio_slowdown = 2` required in Python; `--led-slowdown-gpio=2` in C demos
- **PWM conflict**: GPIO 18 (PWM0) used for matrix OE# — onboard audio must be disabled
  (`dtparam=audio=off` in `/boot/config.txt`, confirmed surviving reboot)
- CPU isolation: `isolcpus=3` added to `/boot/cmdline.txt` for better matrix timing
- CPU: 4× Cortex-A53 @ 1.2GHz — sufficient; keep image pipeline lightweight

### Volumio OS
- **Debian Buster** (not Bullseye as initially assumed) — Python 3.7, GCC 8
- Standard apt, systemd available
- User customizations to `/boot/config.txt` should go in `/boot/userconfig.txt`
  to survive Volumio system updates — `install.sh` will write there

### HUB75E Panel (64×64) — Seengreat P3.0-64x64
- 5-bit row addressing (A/B/C/D/E) — HUB75E, not standard 4-bit HUB75
- 1/32 scan rate, 5V/4A power (separate rail from Pi)
- Internal GBR color ordering — **compensated by the seengreat wiring table in hardware**;
  do NOT set `led_rgb_sequence = 'GBR'` in software (double-corrects, scrambles colors)
- **Panel orientation**: software coordinate origin (0,0) appears at physical top-right
  when HUB75 input connector faces a specific direction — correct with `Rotate:270`
  pixel mapper. Easy to change in config if panel is remounted.
- Driver IC: unknown (not documented by seengreat); behaves correctly with default settings

### Bonnet Configuration (production)

When Bonnet #3211 is installed, update `display.py`:
```python
opts.hardware_mapping = 'adafruit-hat'   # was 'regular'
opts.disable_hardware_pulsing = False    # Bonnet handles PWM properly
```
With the Bonnet, OE# is routed off GPIO 18, so `dtparam=audio=off` is no longer required.

### GPIO Wiring (direct to Pi — development only, causes flicker)

Using seengreat wiki Table 2-1 — matches hzeller "regular" default mapping:

| Signal | BCM GPIO | Header Pin |
|---|---|---|
| R1 | 11 | 23 |
| G1 | 27 | 13 |
| B1 | 7 | 26 |
| R2 | 8 | 24 |
| G2 | 9 | 21 |
| B2 | 10 | 19 |
| CLK | 17 | 11 |
| OE | 18 | 12 |
| LAT | 4 | 7 |
| A | 22 | 15 |
| B | 23 | 16 |
| C | 24 | 18 |
| D | 25 | 22 |
| E | 15 | 10 |
| GND | GND | 6, 9, 14… |

### Power Architecture

**With Bonnet (production):**
```
Wall ──► 5V 4A PSU ──► Bonnet barrel jack (2.1mm, center positive)
                              │
                              ├──► Pi 5V rail (via GPIO header, replaces micro-USB)
                              └──► Panel VCC/GND (via Bonnet screw terminals + power harness)
```
Single PSU powers everything through the Bonnet.

**Direct GPIO (development, no Bonnet):**
```
Wall ──► 5V 4A PSU ──► Panel VCC/GND (power harness, - terminal = DC return/GND)
Wall ──► 5V 2.5A PSU ──► Pi micro-USB
Pi GND pin ──► Panel GND (common ground required)
```

## Software Architecture

### Runtime
- **Python 3.7** (Volumio on Buster — not 3.11+ as originally planned; code must be 3.7-compatible)
- Runs as a systemd service, starts after Volumio (`After=volumio.service`)
- Drops privileges after GPIO initialization
- Logging via Python `logging` module to journald

### Components

**`volumio_client.py`** — Volumio integration
- Primary: Socket.io subscriber to `pushState` event
- Fallback: REST poll of `http://volumio.local/api/v1/getstate` if Socket.io disconnects
- Reconnect loop with exponential backoff
- Albumart URL normalization: prepend `http://volumio.local` to relative `/albumart` paths

**`display.py`** — Image pipeline
1. Fetch albumart via HTTP (cached by URL to avoid redundant fetches)
2. LANCZOS resize to 64×64
3. Gamma correction via 768-entry LUT (configurable, default γ=2.2)
4. Push to matrix via rgbmatrix Python bindings (`SetImage(unsafe=False)` for 3.7 compat)

**`vinyltron.py`** — Orchestrator daemon
- Wires volumio_client → display
- Handles state: playing / paused / stopped → show art or fallback
- Manages graceful shutdown (SIGTERM)

### Volumio pushState Payload (relevant fields)
```json
{
  "status": "play|pause|stop",
  "title": "...",
  "artist": "...",
  "album": "...",
  "albumart": "/albumart?...",
  "duration": 245,
  "seek": 42000,
  "samplerate": "44.1 KHz",
  "bitdepth": "16 bit",
  "trackType": "flac"
}
```

### Configuration (`config.toml`)
```toml
[volumio]
host = "volumio.local"
port = 3000

[display]
brightness = 80          # 0-100
gamma = 2.2
slowdown_gpio = 2        # Pi 3B = 2, Pi 5 = 4
rows = 64
cols = 64
rotation = 270           # Rotate:270 corrects panel orientation; change if remounted
panel_type = ""          # set to "FM6126A" if colors/timing are wrong

[fallback]
image = "assets/idle.png"
```

## rpi-rgb-led-matrix Build

Must build from source. Current HEAD fails to compile on Buster/GCC8 due to Pi 5 RP1
code. **Check out the last commit before RP1 support was added:**

```bash
git clone https://github.com/hzeller/rpi-rgb-led-matrix
cd rpi-rgb-led-matrix
git checkout $(git log --oneline -- lib/rp1/ | tail -1 | awk '{print $1}')^
make -C examples-api-use
```

Confirmed working commit: `e947417` ("Merge pull request #1885 from ty-porter/patch-2")

### Python Bindings

This commit predates `pyproject.toml`. Build manually with Cython:

```bash
sudo apt-get install -y cython3
cd bindings/python
# setup.py and rgbmatrix/shims/Imaging.h are provided in this repo under
# rpi-rgb-led-matrix/bindings/python/ — scp them to the Pi before building
python3 setup.py build_ext --inplace
```

The `Imaging.h` stub defines a minimal `ImagingMemoryInstance` struct matching
Pillow 5–9 layout on 32-bit ARM, avoiding the need for Pillow dev headers.

Use `sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')` to import.
