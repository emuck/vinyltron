# Features & Roadmap

## Phase 1 — MVP (current)

- [x] Display current album art on 64×64 HUB75E matrix
- [x] Subscribe to Volumio Socket.io `pushState` for real-time track changes
- [x] Image pipeline: LANCZOS resize → gamma correction → push
- [x] Graceful reconnect if Volumio restarts (exponential backoff + REST fallback)
- [x] `config.toml` for host, brightness, gamma, rotation, panel type flag
- [ ] Fallback image (`assets/idle.png` path wired up; image not yet created)
- [ ] Run as systemd service (`install.sh` + `vinyltron.service` pending)
- [ ] SIGHUP config reload (stub in place, not yet implemented)

## Phase 2 — Overlays + Volumio Plugin

Album art stays full 64×64. Overlays are optional layers rendered on top.

### 2a — Overlay: Progress Bar

Two-pixel strip at the bottom edge of the panel, semi-transparent blend with art:

```
┌────────────────────────────────┐
│                                │
│        full album art          │
│                                │
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒│  ← row 62: art darkened ~40%
│████████████████░░░░░░░░░░░░░░░│  ← row 63: filled = elapsed
└────────────────────────────────┘
```

Derived from `seek` + `duration` fields in Volumio `pushState`. No text, purely visual.

### 2b — Overlay: Format Badge

Small pixel-art icon in a configurable corner. Encodes format tier via both color and
waveform shape — no text required, readable at distance.

| Tier | Formats | Color | Pixel Art |
|---|---|---|---|
| Lossy | MP3 / AAC / OGG | `#666` gray | Square wave |
| CD | 16-bit / 44.1kHz | `#FFF` white | Smooth sine |
| Hi-Res | 24-bit / ≥88.2kHz | `#4AF` blue | Dense sine |
| Ultra | 24-bit / ≥176kHz | `#08F` bright blue | Very dense sine |
| DSD | DSD64/128/256/512 | `#FB0` amber | 1-bit stipple |
| MQA | MQA-tagged | `#A4F` purple | Folded sine |

Badge sprites (~10×8px) stored as numpy arrays in `assets/badges/`. User-replaceable —
drop a custom `.npy` file to override any tier's artwork.

Auto-detected from Volumio `pushState` fields (`trackType`, `samplerate`, `bitdepth`):
```
dsf / dff                              → DSD (amber)
flac/wav, bitdepth=24, sr ≥ 176400    → Ultra (bright blue)
flac/wav, bitdepth=24, sr ≥ 88200     → Hi-Res (blue)
flac/wav, bitdepth=16, sr = 44100     → CD (white)
mp3 / aac / ogg                        → Lossy (gray)
```

### 2c — Volumio Plugin (settings integration)

Native Volumio plugin (Node.js shell + UIConfig.json) exposing settings directly in
Volumio's UI under Settings → Plugins → Voluma. No separate web UI or SSH required.

Settings exposed:
- Show progress bar (toggle)
- Show format badge (toggle)
- Badge position (top-left / top-right / bottom-left / bottom-right)
- Brightness (slider 0–100)
- Gamma (select: 1.8 / 2.0 / 2.2 / 2.4)

On save: plugin writes `config.toml`, sends `SIGHUP` to vinyltron daemon → daemon reloads
config without restart.

**Publication goal:** Submit to Volumio plugin store as open-source alternative to
commercial album art displays (e.g. TuneShine at $199 — our BOM is ~$67, and we support
Volumio natively where they don't).

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
