# Engineering Spec

## System Overview

Vinyltron is a Linux daemon running on a Raspberry Pi alongside Volumio. It subscribes
to Volumio's Socket.io `pushState` event stream for real-time track change notifications,
fetches album art, processes it through an image pipeline, and pushes frames to a 64×64
HUB75E RGB LED matrix via the rpi-rgb-led-matrix C library.

The plugin targets **Volumio 4 / Bookworm** for store submission. Development and testing
were done on Volumio 3 / Buster; the daemon is Python 3.7+ compatible and runs on both.

## Hardware Constraints

### Raspberry Pi 3B
- GPIO: 3.3V logic — direct HUB75E connection runs but causes **vertical column flicker**
  (confirmed 2026-05-23). Root cause: Pi 3B GPIO (3.3V) is below the 5V CMOS VIH threshold
  (0.7×5V = 3.5V) of the panel's row driver ICs. Not software-tunable. Direct GPIO remains
  a supported option if the lower-margin, slightly flickery look is acceptable.
  **Adafruit Bonnet (#3211)** with 74AHCT245 level shifters (VIH ~2.0V) is recommended for
  cleaner and more stable output.
- GPIO speed: `opts.gpio_slowdown = 2` with the bonnet; `4` caused more horizontal flicker in testing
- Bonnet refresh limiting: `opts.limit_refresh_rate_hz = 120` reduced horizontal static substantially during testing; packaged default is `0` for uncapped driver behavior
- Bonnet quality/PWM mode: bridge `GPIO4` to `GPIO18` and use `hardware_mapping = "adafruit-hat-pwm"` for cleaner OE timing
- **PWM conflict**: GPIO 18 (PWM0) is used for matrix OE# in hardware-pulse mode, which
  conflicts with onboard audio (`snd_bcm2835`) on Volumio 4 / Bookworm. See "Bonnet
  Configuration" below for the fix and how `install.sh` automates it.
- CPU: 4× Cortex-A53 @ 1.2GHz — sufficient; keep image pipeline lightweight

### Volumio OS
- **Debian Buster** (Volumio 3, tested) — Python 3.7, GCC 8
- **Debian Bookworm** (Volumio 4, store target) — Python 3.11, Node ≥ 20
- Standard apt, systemd available
- User customizations to `/boot/config.txt` should go in `/boot/userconfig.txt`
  to survive Volumio system updates

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

With Bonnet #3211 installed in quality/PWM mode:
```python
opts.hardware_mapping = 'adafruit-hat-pwm'
opts.disable_hardware_pulsing = False
opts.limit_refresh_rate_hz = 0  # uncapped by default; try 90-140 if flicker/hiccups appear
```

Manual hardware requirements:
- `E` bridged to `8` on the panel for 64-row HUB75E support
- Quality jumper wire from `GPIO4` to `GPIO18`, so GPIO18 (PWM0) is reserved for matrix
  OE# timing

Boot config requirements (GPIO18/PWM must be free of onboard audio): `dtparam=audio=off`
in `/boot/userconfig.txt`, and `/boot/cmdline.txt` must not contain
`snd_bcm2835.enable_hdmi=1`/`enable_headphones=1` — instead it should have
`module_blacklist=snd_bcm2835 modprobe.blacklist=snd_bcm2835` (Volumio 4/Bookworm's
default `cmdline.txt` includes the `enable_*` args, which re-enable the module). As of
v0.2.4, `install.sh` makes both changes automatically and idempotently (backs up the
originals as `cmdline.txt.vinyltron-orig` and `userconfig.txt.vinyltron-orig`) and
prints a reboot reminder if anything changed — no manual boot-file editing required. Confirmed 2026-06-10 on Volumio 4.119 / kernel
`6.12.74-v7+`: `snd_bcm2835` stays absent from `/proc/modules` and `rpi-rgb-led-matrix`
runs with `disable_hardware_pulsing = False` without flicker.

As a last-resort fallback, `display.py` also detects a still-loaded `snd_bcm2835` at
startup and forces software-pulse mode — see "Components" below.

Without the quality jumper, use `hardware_mapping = 'adafruit-hat'`.

### GPIO Wiring (direct to Pi — optional, lower signal margin)

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

**With Bonnet (recommended):**
```
Pi USB-C PSU ──► Pi + Waveshare display
5V 4A matrix PSU ──► Panel/bonnet matrix 5V input
Bonnet/ribbon ──► HUB75 data/control with shared ground
```
Do not rely on Pi USB-C back-powering the matrix. The matrix must draw from the dedicated 5V rail; grounds remain common through the bonnet/ribbon/power wiring.

**Direct GPIO (optional, no Bonnet):**
```
Wall ──► 5V 4A PSU ──► Panel VCC/GND (power harness, - terminal = DC return/GND)
Wall ──► 5V 2.5A PSU ──► Pi micro-USB
Pi GND pin ──► Panel GND (common ground required)
```

## Software Architecture

### Runtime
- **Python 3.7+** — tested on Buster/Volumio 3.x (Python 3.7); plugin targets Bookworm/Volumio 4 (Python 3.11)
- Runs as a systemd service, starts after Volumio (`After=volumio.service`), runs as root
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

Two startup checks force `disable_hardware_pulsing = True` regardless of
`config.toml`, each working around a different uncatchable failure in the underlying C
library:
- `/proc/modules` shows `snd_bcm2835` loaded — the C library calls `exit(1)` if hardware
  pulsing is requested while that module is loaded. See "Bonnet Configuration" above.
- `/proc/device-tree/model` identifies a Raspberry Pi 5 — hardware-pulse mode busy-spins
  and hangs the daemon on Pi 5's RP1 chip. See "rpi-rgb-led-matrix Build" below.

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
- Native Volumio plugin writes v-conf settings and patches
  `/data/configuration/user_interface/vinyltron/config.toml`
- The plugin package bundles the Python daemon under
  `/data/plugins/user_interface/vinyltron/vinyltron`
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
slowdown_gpio = 2        # Bonnet test value; 4 caused more horizontal flicker on current panel
limit_refresh_rate_hz = 0      # 0 = uncapped; 90-140 is a practical tuning range
startup_delay_seconds = 5 # extra grace period after Volumio /status returns ready before idle display starts
rows = 64
cols = 64
rotation = 270           # Rotate:270 corrects panel orientation; change if remounted
hardware_mapping = "adafruit-hat-pwm"
disable_hardware_pulsing = false
display_on = true
panel_type = ""          # set to "FM6126A" if colors/timing are wrong

[schedule]
enabled = false
on_time = "08:00"
off_time = "23:00"

[fallback]
image = "assets/idle.png"
image_folder = "/data/INTERNAL/Vinyltron/idle-images"
mode = "single"          # single | selected | random_folder | screensaver
selected_image = ""      # basename inside image_folder
rotate_seconds = 300

[screensaver]
engine = "brians_brain"  # brians_brain | langtons_ant | chaos_game | gray_scott
palette = "cyan_amber"   # cyan_amber | green_magenta | blue_red | white_violet
fps = 6                  # clamped to 2-24
reset_seconds = 300      # 0 disables periodic random reset
density = 0.22           # advanced Brian's Brain initial ready-cell density
ant_count = 4            # advanced Langton's Ant count
steps_per_frame = 96     # advanced Langton's Ant simulation steps per rendered frame
points_per_frame = 320   # advanced Chaos Game plotted points per rendered frame
fade = 12                # advanced Chaos Game per-frame fade
rotation_speed = 2       # advanced Chaos Game vertex rotation degrees per rendered frame
feed = 0.055             # advanced Gray-Scott reaction-diffusion feed rate
kill = 0.062             # advanced Gray-Scott reaction-diffusion kill rate
grid_scale = 2           # advanced Gray-Scott downscale factor (2 = 32x32 grid upscaled to 64x64)
seed = ""                # advanced deterministic seed; blank = random each daemon start

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
| MP3 with zero-valued bitrate | Treat `0` as unknown and show `MP3` unless MPD reports a valid bitrate |

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
| `screensaver` | Run the selected `[screensaver].engine` as the fallback background. |

Folder images are not modified on disk. `display.py` opens them on demand, applies EXIF
transpose, converts to RGB, center-crops to square, resizes to 64x64, applies the active
gamma LUT, and renders them. Random selection happens only when the fallback state is
entered after debounce, not on every render.

Screensaver fallback is controlled by `[screensaver]`. The plugin UI exposes generic
controls (`engine`, `palette`, `fps`, `reset_seconds`) while engine-specific tuning such as
Brian's Brain `density`, Langton's Ant `ant_count`/`steps_per_frame`, Chaos Game
`points_per_frame`/`fade`/`rotation_speed`, Gray-Scott `feed`/`kill`/`grid_scale`, and `seed`
remains config-file-only. Brian's Brain is a three-state cellular automaton backed by two
4096-byte grids and precomputed neighbor indexes. Langton's Ant maintains a one-byte grid
and a small set of moving ants that turn, flip cells, and wrap around the panel edges.
Chaos Game plots random midpoint steps toward rotating triangle vertices into a decaying
RGB buffer. Gray-Scott runs a two-chemical reaction-diffusion simulation (the classic
Gray-Scott model with a 9-point Laplacian) on a downscaled grid, mapped through a color
gradient and bilinear-upscaled to the panel size, producing slowly evolving coral/maze
patterns. All engines render generated RGB frames through the same `display.py` image path
as static fallbacks, so progress and format overlays still compose on top.

During early service startup, `vinyltron.py` polls Volumio's `/status` endpoint before
initializing the matrix display for any idle fallback mode. Idle display starts only after
`/status` returns `ready` and the extra `[display].startup_delay_seconds` grace period has
elapsed. Playback artwork is allowed to initialize the matrix immediately. If `/status`
never reports `ready`, `VOLUMIO_READY_MAX_WAIT_SECONDS` (5 minutes) bounds the wait and the
idle display starts anyway, so a broken or slow Volumio doesn't leave the matrix blank
indefinitely. The frame, reset, and delayed-start timers are owned by `vinyltron.py` and are
cancelled on playback artwork, display-off, config reload, and shutdown.

For visual tuning before hardware deployment, `tools/matrix-sim.py` exposes the same
generated-frame boundary in a browser: engines return 64x64 RGB frames, `/api/frame`
returns 12288 raw RGB bytes, and the browser canvas renders them as a scaled matrix. See
[matrix-simulator.md](matrix-simulator.md).

For photo-frame use, `tools/convert-idle-images.py` can pre-convert source photos into
64x64 optimized PNGs before they are copied to `image_folder`. This reduces storage,
startup decode cost, and idle-rotation CPU work. HEIC/HEIF files are supported through
Pillow if available, otherwise ImageMagick `magick`, otherwise macOS `sips`.

The plugin also serves a phone-friendly photo manager. The default URL is
`http://volumio.local:3018/photos`, and the port is stored in Volumio plugin config as
`photo_manager_port` rather than in daemon `config.toml`. Users can change it from the
Idle Image settings page if port `3018` conflicts with another local service. The manager
can upload, list, select, delete, and enable random idle photos. Uploads are written to a
temporary file, converted by the bundled Python/Pillow helper `photo_upload_convert.py`,
and stored as optimized 64x64 PNG files under `image_folder`; uploaded originals are
discarded.

### Display Schedule

The optional `[schedule]` section controls idle/photo-frame display time:

- `display_on = false` is a hard master off and blanks the matrix.
- When `display_on = true`, schedule windows gate idle/photo-frame display.
- Active Volumio `play` or `pause` state wakes the matrix outside the schedule only when
  `[volumio] artwork_enabled = true`.
- Overnight windows are supported, for example `on_time = "18:00"` and
  `off_time = "01:00"`.

## rpi-rgb-led-matrix Build

Must build from source — no prebuilt wheels exist, and a single prebuilt `.so` would not
be portable across the Cortex-A core variants in Pi 3B/4/5 (the library's `config.mk` uses
`-march=native -mtune=native`). `plugin/install.sh` builds it automatically on first
install — see "Automated Install" below for what it does.

**Pinned commit**: `e947417` ("Merge pull request #1885 from ty-porter/patch-2"), full SHA
`e947417fff9042b3ea173542be09490acab069f7`. Upstream HEAD fails to compile on Buster/GCC8
due to Pi 5 RP1 code, and this commit predates Pi 5 RP1 GPIO support entirely — see
the Pi 5 note in `README.md`.

Verified 2026-06-11/12 on a Pi 5 (Volumio 4.119/Bookworm, armhf userspace): `install.sh`
completes, `rgbmatrix` imports, and the daemon starts, connects to Volumio, and shuts down
cleanly (~1s) in software-pulse mode (`disable_hardware_pulsing = True`).

**Confirmed broken on Pi 5**: hardware-pulse mode (`disable_hardware_pulsing = False`)
against the RP1 I/O chip — this pinned commit predates RP1 GPIO support. Rather than
failing to initialize, the C library's PWM setup busy-spins and holds the GIL, so the
daemon never responds to SIGTERM (`systemctl stop` hangs 90s and requires SIGKILL).
`display.py` detects Pi 5 and forces `disable_hardware_pulsing = True` regardless of
`config.toml`, so this can no longer happen — see "Components" above. Actual HUB75
panel rendering on Pi 5 remains untested: mounting the Bonnet on a Pi 5 requires a tall
GPIO stacking header (~12-15mm) to clear the Active Cooler, which the test unit doesn't
have. Pi 3B remains the verified reference platform for hardware-pulse mode and panel
rendering.

### Python Bindings

This commit predates `pyproject.toml`, so the Python bindings need a custom `setup.py`
and an `Imaging.h` stub (a minimal `ImagingMemoryInstance` struct matching Pillow 5–9's
layout on 32-bit ARM, avoiding a dependency on Pillow dev headers). Both live in
`tools/matrix-build/` in this repo and are bundled into the plugin package as
`vinyltron/matrix-build/`, so `install.sh` can build the bindings without network access
to this repo.

Use `sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')` to import.

### Automated Install (plugin/install.sh)

On first install, if `rgbmatrix` isn't importable from `/home/volumio/rpi-rgb-led-matrix`,
`install.sh`:
1. Installs build dependencies (`build-essential python3-dev python3-pip cython3 wget
   libjpeg-dev zlib1g-dev`), retrying with `--force-overwrite` for the known
   `libpython3-stdlib` conflict on fresh Bookworm images.
2. Downloads the pinned commit as a tarball from
   `https://github.com/hzeller/rpi-rgb-led-matrix/archive/<sha>.tar.gz` (no `git` needed).
3. Runs `make -C examples-api-use`, then builds the Python bindings using the bundled
   `matrix-build/` helpers (above).

The result persists at `/home/volumio/rpi-rgb-led-matrix` across plugin reinstalls/updates
(uninstall.sh does not remove it), so the build only runs once per device.

Measured on a Pi 3B (full rebuild, from `systemctl stop` to `plugininstallend`): ~24
minutes total — `make -C examples-api-use` (library + 9 binaries) takes ~19 minutes and
the Cython Python bindings take ~4 minutes, plus apt/pip/systemd overhead. Budget roughly
25-30 minutes for a first install on a Pi 3B.

Measured on a Pi 5 (fresh install, `install.sh starting` to `plugininstallend`): ~3
minutes total — `make -C examples-api-use` ~42s, Cython bindings ~12s, apt/pip dominate
the rest (including building Pillow from source).

**Volumio runs `install.sh` via `/bin/sh` (dash), ignoring the `#!/bin/bash` shebang** —
confirmed via `journalctl -u volumio` showing `COMMAND=/usr/bin/sh .../install.sh`. dash
does not support `set -o pipefail`, so the script uses plain `set -e` and avoids any
`cmd | other_cmd` pipeline whose exit status matters (e.g. the matrix tarball is
downloaded with `wget -qO file` then extracted with `tar -f file`, not `wget -qO- | tar`).

## libheif Build

Bookworm/Raspbian ships `libheif1`/`libheif-examples` 1.15.1, which rejects HEIC photos
from iPhone 15 Pro+ running iOS 18: `Could not read HEIF/AVIF file: Invalid input:
Unspecified: Too many auxiliary image references`. These photos store an HDR "gain map" as
an auxiliary image shared between two main images in an `altr` group, a structure libheif
1.15.1 rejects as a sanity-check violation. Fixed upstream in libheif 1.18.0
([strukturag/libheif#1147](https://github.com/strukturag/libheif/issues/1147)).

**Source: `bookworm-backports`**, which ships `libheif1`/`libheif-examples` 1.19.7 prebuilt
for armhf — past the 1.18.0 fix. Building libheif from source was tried first but ruled
out: a Pi 3B has 869MB RAM and no swap by default, and `/` is an overlay filesystem
(`lowerdir`/`upperdir` from the initramfs, not reachable from the running system), so a
swapfile can't be created to give the C++ compiler enough headroom — `box.cc` either
thrashes the system for over an hour or gets OOM-killed.

### Automated Install (plugin/install.sh)

After the required build dependencies are installed, `install.sh` adds
`/etc/apt/sources.list.d/vinyltron-backports.list`
(`deb http://deb.debian.org/debian bookworm-backports main`) and refreshes apt metadata.
The Debian 12 archive signing key is already trusted on Raspbian Bookworm images
(`/etc/apt/trusted.gpg.d/debian_12.gpg`), so no keyring setup is needed. `apt-get install
-y -t bookworm-backports libheif-examples` then pulls `libheif-examples`/`libheif1` 1.19.7
from backports (default backports priority 100 means this doesn't affect any other
package's install/upgrade candidate). This installs to `/usr/bin`, so
`photo_upload_convert.py`'s `shutil.which("heif-convert")` picks it up directly — no PATH
changes needed.

Both the backports metadata refresh and the package install are optional. A failure (e.g.
backports unreachable) prints a warning and lets the rest of `install.sh` continue, instead
of `set -e` + the `exit_cleanup` trap uninstalling the whole plugin over an optional HEIC
feature.
