# Test Procedure

---

## Pi 3B / Volumio Prep (completed 2026-05-23)

- [x] `dtparam=audio=off` added to `/boot/config.txt`
- [x] `isolcpus=3` appended to `/boot/cmdline.txt`
- [x] Build tools already present on Volumio (git, build-essential, python3-dev, python3-pip)
- [x] rpi-rgb-led-matrix cloned and checked out to pre-RP1 commit `e947417`
- [x] `make -C examples-api-use` — built successfully
- [x] `cython3` installed, Python bindings built with custom `setup.py` + `Imaging.h` stub

---

## 1. Wiring (direct GPIO, no Bonnet)

Follow seengreat wiki Table 2-1 — see `engineering-spec.md` for full pin table.
Critical: connect PSU GND to a Pi GND pin for common ground.

Power sequence: Pi first, matrix PSU second.

---

## 2. C Demo Smoke Test

```bash
cd ~/rpi-rgb-led-matrix
sudo ./examples-api-use/demo -D 0 \
  --led-rows=64 --led-cols=64 \
  --led-slowdown-gpio=2 \
  --led-no-hardware-pulse
```

Expected: full 64×64 panel cycling colors. No `--led-rgb-sequence=GBR` needed —
seengreat wiring corrects color ordering in hardware.

**If only top 32 rows light up:** E address pin (GPIO 15, header pin 10) not connected.

---

## 3. Python Bindings Smoke Test

```bash
sudo python3 ~/test_matrix.py
```

`test_matrix.py` sets four corners to distinct colors with `Rotate:270` applied.
Expected: RED top-left, GREEN top-right, BLUE bottom-left, YELLOW bottom-right.

✅ Confirmed working 2026-05-23.

**Key findings from hardware testing:**
- `led_rgb_sequence = 'GBR'` must NOT be set — seengreat wiring corrects in hardware
- `pixel_mapper_config = 'Rotate:270'` required for correct orientation
- `disable_hardware_pulsing = True` required for direct GPIO (no Bonnet)
- Python bindings: `sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')`

---

## 4. Volumio Socket.io Smoke Test

Install dependency first:
```bash
sudo pip3 install python-socketio[client]
```

Then:
```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')
import socketio

sio = socketio.Client()

@sio.on('pushState')
def on_state(data):
    print("status:", data.get('status'))
    print("title:", data.get('title'))
    print("albumart:", data.get('albumart'))
    sio.disconnect()

sio.connect('http://volumio.local:3000')
sio.emit('getState', '')
sio.wait()
EOF
```

Expected: prints current playback state. Start playing something in Volumio first.

---

## 5. End-to-End Test

- [x] Deploy via `./deploy.sh` from Mac for daemon-only development
- [x] Reinstall/update plugin and bundled daemon via `./dev-install-plugin.sh` from Mac
- [x] Build plugin zip with `./tools/build-volumio-plugin.sh`
- [ ] Build release-style plugin zip with `./tools/build-volumio-plugin.sh --with-node-modules`
- [ ] Install generated zip through Volumio CLI with `./tools/install-volumio-plugin-zip.sh`
- [x] Start vinyltron manually from the plugin-owned daemon path if needed:
  `sudo python3 /data/plugins/user_interface/vinyltron/vinyltron/vinyltron.py /data/configuration/user_interface/vinyltron/config.toml`
- [x] Start vinyltron as a service: `sudo systemctl start vinyltron`
- [x] Play a track in Volumio — album art appears within 2 seconds
- [x] Skip track — art updates without restart
- [x] Volumio Socket.io disconnect — vinyltron reconnects automatically
- [ ] Pause — art remains visible and progress stops advancing
- [ ] Stop — fallback image shown after the 1.5 second fallback debounce
- [ ] Reboot Pi — vinyltron starts after Volumio automatically

Useful service commands:
```bash
sudo systemctl restart vinyltron
sudo systemctl reload vinyltron
journalctl -u vinyltron -f
```

Development deployment note: `./deploy.sh` preserves the legacy Pi runtime `config.toml`
by default. The plugin-owned install path uses
`/data/configuration/user_interface/vinyltron/config.toml`; use `./dev-install-plugin.sh`
when changing plugin-owned daemon files.
when intentionally replacing the remote config with the repo default.

---

## 6. Overlay Test

### Format Text

Enable in `config.toml` or through the Volumio plugin:
```toml
[overlays]
format_badge = true
format_font = "tom_thumb" # or "tiny5" / "spleen"
badge_duration = 10
```

Expected:
- A compact format label appears at the top-left after the first track of an album starts.
- The label clears after `badge_duration` seconds.
- Track changes within the same album do not briefly show the fallback image and do not
  re-show the label.
- Volumio transient stop events between tracks log `scheduling fallback`, then get
  cancelled by the next play/pause state before the idle image appears.
- New albums re-show the label.
- If album art cannot be fetched for an active track, the idle/fallback image is used as
  the temporary base image and the format label still appears for a new album.
- Changing `Format Font` in the plugin reloads the daemon and affects the next rendered
  format label.

Known examples from Volumio logs:
- `service='spop' trackType='spotify' codec='ogg' samplerate='320 kbps'` -> `320K`, green
- `trackType='mp3' bitrate=None samplerate='44.1 kHz' bitdepth='24 bit'` with MPD `bitrate: 320` -> `MP3 320K`, cyan
- `trackType='mp3' bitrate=None` with no MPD bitrate available -> `MP3`, cyan
- `trackType='m4a' samplerate='44.1 kHz' bitdepth='16 bit'` -> `16/44.1`, white
- `trackType='flac' samplerate='192 kHz' bitdepth='24 bit'` -> `24/192`, white
- `trackType='dsf' samplerate='2.82 MHz' bitdepth='1 bit'` -> `DSD64`, magenta
- `trackType='dsf' samplerate='22.58 MHz' bitdepth='1 bit'` -> `DSD512`, magenta

Font smoke test:
- Select `Format Font = Tiny5` in the plugin.
- Save display settings.
- Confirm journald logs `Loaded format font tiny5`.
- Start a new album and verify the format label is legible and still fits at the top-left.
- Repeat with `Format Font = Spleen 5x8` and confirm journald logs `Loaded format font spleen`.

### Progress Bar

Enable with a nonzero height:
```toml
[overlays]
progress_bar_height = 3
progress_bar_foreground = [255, 255, 255]
progress_bar_background = [] # empty means leave the album art as the unfilled track
```

Expected:
- Filled width is `seek / duration * 64`.
- Updates happen at the next LED-column boundary, so long tracks update less frequently
  and short tracks update more frequently.
- `progress_bar_height = 0` disables the bar.

---

## 7. Plugin Settings Test

From Volumio Settings -> Plugins -> Vinyltron:
- Display settings save with `systemctl reload vinyltron`.
- Idle image settings save with `systemctl reload vinyltron`.
- Rotation saves with `systemctl restart vinyltron`.
- `Progress Height` accepts typed values. Negative values clamp to 0, floats truncate,
  values above 64 clamp to 64.
- `Progress Track = Album Art` stores an empty TOML array and leaves unfilled pixels as
  the cached album art.
- `Format Duration` persists as `badge_duration`.

### Idle Image Folder Test

Default folder:
```bash
/data/INTERNAL/Vinyltron/idle-images
```

Expected:
- Plugin install creates the folder and makes it writable by `volumio`.
- Copying `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, or `.webp` files into the folder makes
  them appear in the `Idle Image` dropdown after reopening the plugin settings page.
- `Idle Mode = Built-in Idle Image` uses `assets/idle.png`.
- `Idle Mode = Selected Folder Image` uses the selected filename.
- `Idle Mode = Random Folder Image` chooses a random valid image each time the real
  fallback state is entered after debounce.
- The built-in `assets/idle.png` is not included in random-folder mode unless a copy is
  also placed in `/data/INTERNAL/Vinyltron/idle-images`.
- Portrait and landscape images are center-cropped to square and rendered as 64x64.
- Empty folders, missing selected files, and corrupt files fall back to `assets/idle.png`.

### Idle Photo Import Workflow

Convert source photos on the Mac before copying them to Volumio:

```bash
python3 tools/convert-idle-images.py "$HOME/Downloads/convert" /tmp/vinyltron-idle --recursive
rsync -avz /tmp/vinyltron-idle/ volumio@192.168.88.50:/data/INTERNAL/Vinyltron/idle-images/
```

Expected:
- Output files are optimized 64x64 PNGs, typically under 15 KB each.
- HEIC/HEIF iPhone photos are accepted when ImageMagick `magick` or macOS `sips` is
  available.
- Reopen the plugin settings page and confirm the new PNG files are visible in the idle
  image folder.
- Set `Idle Mode = Random Folder Image` and `Photo Interval (seconds)` to a short value,
  such as `60`, to confirm images rotate while Volumio is stopped.

---

## 8. Known Follow-Up Checks

### Overlay Startup After Upgrade

Observed once: immediately after upgrade, the progress bar and format text did not appear.
After changing plugin settings and reloading, overlays eventually started again.

If this repeats, capture:
```bash
journalctl -u vinyltron -b --no-pager | tail -120
cat /data/configuration/user_interface/vinyltron/config.toml
```

Check for:
- `SIGHUP received` after plugin settings are saved.
- `Config startup:` and `Config reload:` lines showing expected overlay values.
- `[overlays] format_badge`, `badge_duration`, and `progress_bar_height` values in
  `/data/configuration/user_interface/vinyltron/config.toml`.
- `Volumio format:` and `Format overlay:` log lines on new albums.
- `Album art unavailable; showing fallback for current track` followed by `Format overlay:`
  when Volumio returns invalid album art for an active track.
- Whether the daemon was restarted or only reloaded after deploy.

### Idle Image Troubleshooting

If idle images do not appear, capture:
```bash
ls -la /data/INTERNAL/Vinyltron/idle-images
journalctl -u vinyltron -b --no-pager | tail -120
```

Check for:
- `Config startup:` or `Config reload:` showing expected `fallback_mode`,
  `fallback_folder`, `fallback_selected`, and `volumio_artwork_enabled` values.
- `Loaded idle image ...` when fallback is shown.
- `Could not load idle image ...` warnings for corrupt or unreadable files.
