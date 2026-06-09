# Features & Roadmap

## Next Actions

### Release / Revision Tracking

Status: implemented.

Behavior:
- `VERSION` is the daemon version and is logged at startup.
- `plugin/package.json` owns the Volumio plugin package version.
- `CHANGELOG.md` records user-facing changes.
- `docs/release.md` defines the release checklist and tag format.
- Git tags use `vX.Y.Z`.

### Volumio Ecosystem Packaging Goal

Goal: make Vinyltron installable as a normal Volumio plugin without a separate developer
deploy flow.

Target architecture:
- Plugin package owns installation end-to-end: daemon files, assets, Python requirements,
  systemd service, and Volumio settings UI.
- Plugin package bundles daemon files under the plugin directory at
  `/data/plugins/user_interface/vinyltron/vinyltron`.
- `plugin/install.sh` installs Python dependencies, creates/enables `vinyltron.service`,
  migrates an existing legacy config if present, and writes the minimal sudoers rules
  needed for start/stop/reload/restart.
- Plugin settings patch `/data/configuration/user_interface/vinyltron/config.toml` and
  reload or restart the daemon as appropriate.
- End users should not need `deploy.sh`; that remains a development helper only.
- Plugin metadata should be cleaned up for public submission, including package fields,
  descriptions, install behavior, uninstall behavior, and release packaging with
  `node_modules` included only in generated artifacts.

Publication path to investigate:
- Current Volumio plugin source flow uses the Bookworm plugin source repository and
  `volumio plugin submit` for review/beta promotion.
- Older Volumio 3 plugin sources are effectively maintenance-only, so decide whether this
  targets Volumio 3 local install first, Volumio 4 public submission, or both.
- Before submission, add a fresh install test on a clean Volumio image and an upgrade test
  over an existing local install.

### Idle Image Upload + Pruner

Status: implemented.

Goal: make idle/photo-frame image management possible from a phone while keeping the
runtime asset simple and bounded. Uploaded originals are treated as temporary input only.

Implemented behavior:
- Keep `[fallback] image = "assets/idle.png"` as the stable daemon path.
- Add `[fallback] image_folder = "/data/INTERNAL/Vinyltron/idle-images"`.
- Add `[fallback] mode = "single"` with modes `single`, `selected`, and `random_folder`.
- Add `[fallback] selected_image = ""` as a basename inside `image_folder`.
- Plugin settings expose Idle Mode, Idle Folder, and a dynamically populated Idle Image
  dropdown from supported image files in the folder.
- Built-in idle mode uses `assets/idle.png`; random-folder mode only uses images from
  `image_folder`, so the built-in image is not part of the random pool unless copied there.
- Folder images are loaded only when a real fallback occurs after debounce, then converted
  to RGB, center-cropped to square, resized to 64x64 with LANCZOS, gamma-corrected, and
  shown. The source images are not overwritten.
- Optional pre-conversion is available with `tools/convert-idle-images.py` for photo-frame
  use. It accepts common image formats plus HEIC/HEIF, applies EXIF orientation, center
  crop, LANCZOS resize, and writes optimized 64x64 PNG files that are cheap to store and
  fast to load.
- The plugin serves a lightweight photo manager at `http://volumio.local:3018/photos`.
  It is designed for iPhone use and can list, upload, select, delete, and enable random
  idle photos without SCP or network-share copying.
- The Volumio settings page shows the photo manager URL in the Idle Image section.
- Uploads are sent to the Node plugin as JSON, written to a temporary file, and converted
  by the bundled Python/Pillow helper `photo_upload_convert.py`. The idle folder receives
  only optimized 64x64 PNG output; uploaded originals are discarded after conversion.
- The manager intentionally avoids native Node image dependencies. HEIC uploads require
  Pillow HEIF support on the Pi or an iPhone camera setting that produces compatible
  image files.
- If selected/random images are missing, invalid, or corrupt, the daemon falls back to
  `assets/idle.png`.
- Plugin install creates `/data/INTERNAL/Vinyltron/idle-images` and makes it writable by
  the `volumio` user.

Validation:
- Open `http://volumio.local:3018/photos` from an iPhone on the same network.
- Upload a portrait photo and a landscape photo; confirm both appear in the grid and in
  the plugin Idle Image dropdown.
- Tap `Select` on one image and confirm `Idle Mode` becomes selected-folder behavior.
- Tap `Use Random Photos`, set a short `Photo Interval (seconds)`, and confirm real
  fallback/idle events rotate through folder images.
- Delete an uploaded image and confirm it disappears from the grid and random pool.
- Confirm corrupt/unsupported uploads return an error without blocking the photo manager.
- Confirm upload/select/delete/random actions reload idle settings without a full restart.

### Configurable Format Text Fonts

Status: implemented.

Behavior:
- `display.py` measures and draws text through a small pixel-font abstraction.
- The built-in 3x5 font is named `tom_thumb` and remains the default/fallback.
- Tiny5 is loaded from `assets/fonts/Tiny5.bdf` when selected.
- Spleen 5x8 is loaded from `assets/fonts/spleen-5x8.bdf` when selected.
- `[overlays] format_font = "tom_thumb"` controls the active font.
- `[overlays] format_font_path = ""` can point to a custom BDF path for future testing.
- The Volumio UI exposes `Format Font` with `Tom Thumb`, `Tiny5`, and `Spleen 5x8` options.
- On config reload, the selected font is reloaded without changing matrix geometry or
  progress bar state.

Validation:
- Python compile checks for daemon files.
- JSON validation for plugin config files.
- `node -c plugin/index.js`.
- `git diff --check`.
- Local stub sanity check that `tiny5` and `spleen` can render the current short
  labels (`320K`, `16/44.1`, `24/192`, `DSD512`) within 64 pixels.

### Startup / Upgrade Overlay Reliability Audit

Observed behavior after upgrade: progress bar and format text may not appear immediately
after deploy/reload, but can start working after changing plugin settings and reloading
again. This needs investigation before treating the overlay startup path as fully stable.

Audit points:
- Confirm v-conf values and `config.toml` remain synchronized after plugin upgrade.
- Confirm plugin install/update copies the latest `config.json` defaults without clobbering
  user settings.
- Confirm `systemctl reload vinyltron` is sent after settings changes and that daemon
  logs show `SIGHUP received`.
- Confirm daemon startup reads persistent config from
  `/data/configuration/user_interface/vinyltron/config.toml` and not an older working
  directory.
- Targeted logging now records daemon startup/reload config snapshots and plugin save/reload
  actions; use those logs to compare v-conf, patched TOML, and daemon runtime state.

## Phase 1 — MVP (current)

- [x] Display current album art on 64×64 HUB75E matrix
- [x] Subscribe to Volumio Socket.io `pushState` for real-time track changes
- [x] Image pipeline: LANCZOS resize → gamma correction → push
- [x] Graceful reconnect if Volumio restarts (exponential backoff + REST fallback)
- [x] `config.toml` for host, brightness, gamma, rotation, panel type flag
- [x] Fallback image (`assets/idle.png`)
- [x] Run as systemd service (`install.sh` + `vinyltron.service`)
- [x] SIGHUP config reload (brightness, gamma, fallback image; geometry requires restart)

## Phase 2 — Overlays + Volumio Plugin (current)

Album art stays full 64×64. Overlays are optional layers rendered on top.

### 2a — Overlay: Progress Bar

Configurable strip at the bottom edge of the panel:

```
┌────────────────────────────────┐
│                                │
│        full album art          │
│                                │
│                                │
│████████████████                │  ← filled width = elapsed / duration * 64
└────────────────────────────────┘
```

Implemented behavior:
- Derived from `seek` + `duration` fields in Volumio `pushState`.
- Height is configurable from 0-64 pixels. `0` disables the bar.
- Foreground color is configurable.
- Background color is configurable; empty background leaves the cached album art visible
  for the unfilled track.
- Updates are scheduled at LED-column boundaries instead of polling Volumio every second.

### 2b — Overlay: Format Text

Compact text in the top-left corner. The label appears once per album and clears after a
configurable duration. This replaced the original 16x16 icon idea because the Volumio
metadata is rich enough to show more useful information in very few characters.

| Source / Format | Example Label | Color |
|---|---|---|
| Spotify / `spop` | `320K` | Green |
| Lossless 16-bit / 44.1 kHz | `16/44.1` | White |
| Lossless 24-bit / 192 kHz | `24/192` | White |
| DSD 2.82 MHz | `DSD64` | Magenta |
| DSD 22.58 MHz | `DSD512` | Magenta |
| MP3 256 kbps | `MP3 256K` | Cyan |

Format detection uses Volumio `pushState` fields: `service`, `trackType`, `codec`,
`bitrate`, `samplerate`, and `bitdepth`. The daemon logs the raw fields to journald so
new services can be classified from real observations. For MPD tracks where Volumio omits
bitrate, Vinyltron asks MPD for its current `status` bitrate before falling back to the
generic MP3 label. Zero-valued bitrates are treated as unknown so transient or VBR-related
metadata does not render as `0K`.

### 2c — Volumio Plugin (settings integration)

Native Volumio plugin (Node.js shell + UIConfig.json) exposing settings directly in
Volumio's UI under Settings -> Plugins -> Vinyltron. A small companion photo manager is
served by the same plugin at `http://volumio.local:3018/photos` for phone uploads and
curation; SSH is not required for normal settings or idle-photo management.

Settings exposed:
- Brightness (select 10-100)
- Gamma (select: 1.8 / 2.0 / 2.2 / 2.4)
- Volumio artwork toggle; disable it to keep idle/photo-frame images on screen
- Progress height (typed 0-64; 0 disables)
- Progress fill color
- Progress track color, including album-art passthrough
- Format overlay toggle
- Format duration (5 / 10 / 15 / 20 / 30 seconds)
- Rotation (restart path)
- Display power toggle
- Daily display power schedule

On save: plugin writes `config.toml`, sends `SIGHUP` to vinyltron daemon → daemon reloads
display settings without restart. Rotation changes require restart because matrix geometry
is configured during `RGBMatrix` construction.

When Volumio artwork is disabled, Vinyltron still watches Volumio state but does not fetch
or display playback album art. The display remains governed by idle settings, including
random folder rotation for photo-frame use. Playback overlays still apply on top of the
idle image: progress follows `Progress Height`, and the format badge follows the existing
`Format Overlay` toggle.

The Power section includes an optional daily schedule with 24-hour `On Time` and
`Off Time` values. `Display On` remains the master switch. When `Display On` is off,
the matrix stays blank. When `Display On` is on, the schedule controls idle/photo-frame
display time, but active `play`/`pause` state with Volumio artwork enabled wakes the
matrix for playback artwork even outside the scheduled window. Overnight windows are
supported, for example `18:00` to `01:00`.

**Publication goal:** Submit to Volumio plugin store as open-source alternative to
commercial album art displays (e.g. TuneShine at $199 — our BOM is ~$67, and we support
Volumio natively where they don't).

## Phase 4 — Vinyl / Analog Source Detection

Fully automatic artwork display for turntable or any analog source — no user interaction required.

### Hardware
- USB audio adapter (~$10) for mic/line input — onboard audio is disabled (GPIO 18 conflict)
- Connect turntable output (after phono preamp) to line in, or use a room microphone

### Detection State Machine

```
IDLE (silence / below threshold)
  ↓  audio RMS above threshold for onset_seconds (~8s)
DETECTING — send 8s clip to recognition API
  ↓  match found → fetch art from MusicBrainz/CoverArtArchive
DISPLAYING artwork
  ↓  silence for silence_seconds (~45s) — needle lifted or between sides
IDLE → show fallback image
  ↓  audio returns → new lookup (Side B, or new record)
DETECTING
```

Between-track gaps (a few seconds) don't re-trigger because silence threshold is ~45s.
Side B is detected automatically: silence when flipping → new lookup when Side B starts.
Surface noise on vinyl is low and constant; music is louder and dynamic — RMS threshold
separates them cleanly without DSP.

### Implementation
- `turntable_client.py` — new source module, same `on_state` callback pattern as `volumio_client.py`
- `[turntable]` section in `config.toml`:
  ```toml
  [turntable]
  enabled = false
  device = "default"          # USB audio device name
  onset_seconds = 8           # sustained audio before triggering lookup
  silence_seconds = 45        # quiet period before returning to idle
  level_threshold = 500       # RMS level distinguishing music from surface noise
  api = "acrcloud"            # acrcloud | audd | shazamio
  api_key = ""
  api_secret = ""
  ```
- Recognition: ACRCloud (recommended — reliable, free tier ~1000/day, plenty for personal use)
- Art fetch: MusicBrainz / CoverArtArchive (free, strong vinyl catalog coverage)

### UX Goal
Put needle on record → artwork appears ~10 seconds later. No app interaction required.

## Phase 3 — Stretch Goals

- [ ] **Brightness by time of day** — dim after 22:00, restore at 08:00
- [ ] **Ambient light sensor** — TSL2591 or VEML7700 via I2C → dynamic brightness
- [ ] **Pause animation** — subtle pulse or dim on pause
- [ ] **Idle screensaver** — slow color wash or vinyl animation when stopped >10 min
- [ ] **128×64 upgrade** — add second panel via `--led-chain=2`, layout: art left + metadata right

## Display Layout

### MVP — Full art
Full 64×64 album art. Clean, no overlays.

### Phase 2 — Art + overlays
Full 64×64 art with optional progress bar (bottom 2px) and format badge (corner, ~10×8px).
Overlays are semi-transparent — art remains the centerpiece.

### Future — 128×64
Two chained 64×64 panels. Left: art. Right: large metadata panel with scrolling title,
artist, format info, progress. Config flag change only — same codebase.
