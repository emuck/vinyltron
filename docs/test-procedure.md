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

- [x] Deploy via `./deploy.sh` from Mac
- [x] Start vinyltron: `sudo python3 /home/volumio/vinyltron/vinyltron.py`
- [x] Play a track in Volumio — album art appears within 2 seconds
- [x] Skip track — art updates without restart
- [x] Volumio Socket.io disconnect — vinyltron reconnects automatically
- [ ] Pause — fallback image shown (untested)
- [ ] Stop — fallback image shown (untested)
- [ ] Reboot Pi — vinyltron starts after Volumio automatically (requires systemd service)
