# Features & Roadmap

## Next Actions

### Configurable Format Text Fonts

Goal: make the current compact format text overlay font-selectable without changing the
format-label logic. Keep the built-in 3x5 font as the default, then add Tiny5 as an
optional BDF-backed font for comparison on the 64x64 panel.

Planned implementation:
- Add a small font abstraction in `display.py` so text fitting, measurement, and drawing
  do not assume fixed 3x5 glyphs.
- Keep the existing built-in font as `tom_thumb` and use it as the default/fallback.
- Add a minimal BDF loader for ASCII glyphs, with Tiny5 loaded from `assets/fonts/Tiny5.bdf`
  when selected.
- Add `[overlays] format_font = "tom_thumb"` to `config.toml` and v-conf defaults.
- Add a Volumio UI select for `Format Font` with `Tom Thumb` and `Tiny5` options.
- On config reload, re-load the selected font without changing matrix geometry or
  interrupting the progress bar logic.

Validation:
- Python compile checks for daemon files.
- JSON validation for plugin config files.
- `node -c plugin/index.js`.
- `git diff --check`.
- Local stub sanity check that both `tom_thumb` and `tiny5` can render the current short
  labels (`320K`, `16/44.1`, `24/192`, `DSD512`) within 64 pixels.

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
new services can be classified from real observations.

### 2c — Volumio Plugin (settings integration)

Native Volumio plugin (Node.js shell + UIConfig.json) exposing settings directly in
Volumio's UI under Settings -> Plugins -> Vinyltron. No separate web UI or SSH required.

Settings exposed:
- Brightness (select 10-100)
- Gamma (select: 1.8 / 2.0 / 2.2 / 2.4)
- Progress height (typed 0-64; 0 disables)
- Progress fill color
- Progress track color, including album-art passthrough
- Format overlay toggle
- Format duration (5 / 10 / 15 / 20 / 30 seconds)
- Rotation (restart path)
- Display power toggle

On save: plugin writes `config.toml`, sends `SIGHUP` to vinyltron daemon → daemon reloads
display settings without restart. Rotation changes require restart because matrix geometry
is configured during `RGBMatrix` construction.

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
