# Engineering Spec

## System Overview

Vinyltron is a Linux daemon running on a Raspberry Pi 3B alongside Volumio 3.x. It subscribes
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

**`display.py`** — Image pipeline and frame compositing
1. LANCZOS resize to 64×64
2. Gamma correction via 768-entry LUT (configurable, default γ=2.2)
3. Cache the last processed full-frame image so overlays can redraw without refetching art
4. Composite optional progress and format-text overlays on a copy of the cached image
5. Push to matrix via rgbmatrix Python bindings (`SetImage(unsafe=False)` for 3.7 compat)

**`vinyltron.py`** — Orchestrator daemon
- Wires volumio_client → display
- Fetches album art via HTTP and discards stale async fetch results when tracks change quickly
- Uses the configured fallback image as the active-track base image if Volumio returns
  invalid or unavailable album art, then reapplies progress and format overlays
- Handles state: playing / paused → show art; stopped → fallback
- Debounces stopped/non-play states for 1.5 seconds so Volumio's transient between-track
  stop events do not flash the idle image or clear album identity
- Tracks album identity separately from track identity so format text is shown once per album
- Derives compact format labels from Volumio fields, e.g. `320K`, `16/44.1`, `24/192`, `DSD512`
- Schedules progress updates at LED-column boundaries instead of polling Volumio every second
- Manages graceful shutdown (SIGTERM/SIGINT) and hot config reload (SIGHUP)

**Volumio plugin** — Settings bridge
- Native Volumio plugin writes v-conf settings and patches `/home/volumio/vinyltron/config.toml`
- Display settings are applied with `systemctl reload vinyltron`
- Rotation requires `systemctl restart vinyltron`

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
display_on = true
panel_type = ""          # set to "FM6126A" if colors/timing are wrong

[fallback]
image = "assets/idle.png"
image_folder = "/data/INTERNAL/Vinyltron/idle-images"
mode = "single"          # single | selected | random_folder
selected_image = ""      # basename inside image_folder

[overlays]
progress_bar = false       # legacy compatibility; progress_bar_height = 0 disables the bar
progress_bar_height = 0
progress_bar_foreground = [255, 255, 255]
progress_bar_background = [] # empty = use album art as the track background
format_badge = false       # compact format text overlay
format_font = "tom_thumb"  # tom_thumb | tiny5 | spleen
format_font_path = ""      # optional custom BDF path
badge_duration = 10
```

### Format Label Rules

The format overlay intentionally stays short enough for a 64-pixel-wide display:

| Volumio fields | Display |
|---|---|
| Spotify / `spop`, `samplerate="320 kbps"` | `320K` in green |
| Lossless 16-bit / 44.1 kHz | `16/44.1` in white |
| Lossless 24-bit / 192 kHz | `24/192` in white |
| DSD 2.82 / 5.64 / 11.28 / 22.58 MHz | `DSD64` / `DSD128` / `DSD256` / `DSD512` in magenta |
| MP3 with bitrate | `MP3 256K` style compact lossy label in cyan |
| MP3 without Volumio bitrate | Query MPD `status` and show `MP3 320K` if MPD reports bitrate; otherwise show `MP3` |

### Format Text Fonts

The default format overlay font is the built-in `tom_thumb` 3x5 pixel font. The daemon
also supports BDF fonts for quick visual experiments. `tiny5` loads
`assets/fonts/Tiny5.bdf`; `spleen` loads `assets/fonts/spleen-5x8.bdf`. If the selected
BDF fails to load, `display.py` logs a warning and falls back to `tom_thumb` so display
startup is not blocked by font issues.

### Idle Images

Fallback image behavior is controlled by `[fallback]`:

| Mode | Behavior |
|---|---|
| `single` | Use `assets/idle.png`. |
| `selected` | Load `image_folder / selected_image`; fall back to `assets/idle.png` on error. |
| `random_folder` | Pick a random supported image from `image_folder` at real fallback time. |

Folder images are not modified on disk. `display.py` opens them on demand, applies EXIF
transpose, converts to RGB, center-crops to square, resizes to 64x64, applies the active
gamma LUT, and renders them. Random selection happens only when the fallback state is
entered after debounce, not on every render.

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
