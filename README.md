# vinyltron

Album art on a 64×64 HUB75E RGB LED matrix, driven by Volumio.

## Prerequisites

The rpi-rgb-led-matrix C library and Python bindings must be built on the Pi before the
plugin will start. SSH in and run:

```bash
sudo apt-get update
sudo apt-get install -y git build-essential python3-dev python3-pip cython3 wget
git clone https://github.com/hzeller/rpi-rgb-led-matrix
cd rpi-rgb-led-matrix
git checkout e947417
make -C examples-api-use
cd bindings/python
wget https://raw.githubusercontent.com/emuck/vinyltron/v0.2.0/tools/matrix-build/setup.py
mkdir -p rgbmatrix/shims
wget -O rgbmatrix/shims/Imaging.h https://raw.githubusercontent.com/emuck/vinyltron/v0.2.0/tools/matrix-build/rgbmatrix/shims/Imaging.h
python3 setup.py build_ext --inplace
```

The `setup.py` and `Imaging.h` stub in `tools/matrix-build/` are custom build helpers —
this commit predates `pyproject.toml`, and `Imaging.h` is a minimal stub that avoids
needing Pillow's dev headers. See [engineering-spec.md](docs/engineering-spec.md#rpi-rgb-led-matrix-build)
for details.

## Install

Download the latest `vinyltron.zip` from [Releases](../../releases), then in Volumio:
**Settings → Plugins → Manual Install → select the zip.**

The plugin bundles the Python daemon, installs a systemd service, and sets up the sudoers
rules needed for service control. No SSH required after the library is built.

## Hardware

| Component | Part | ~Cost |
|---|---|---|
| Display | 64×64 RGB LED matrix, P3, 192×192mm | $37 |
| Interface | Adafruit RGB Matrix Bonnet #3211 | $15 |
| Matrix PSU | 5V 4A switching supply | $12 |
| Host | Raspberry Pi 3B or newer | — |

Matrix power runs on a separate 5V rail. The Bonnet handles 3.3V→5V level shifting
(74AHCT245).

## Pi setup

Three things required before the matrix will work:

- `dtparam=audio=off` in `/boot/config.txt` — PWM conflict between HUB75 OE# and GPIO 18
- Close the HUB75E E-address solder jumper on the Bonnet for 64-row support
- `slowdown_gpio = 2` in `config.toml` (the default)

## What it does

Subscribes to Volumio's `pushState` via Socket.io. On each track change it fetches album
art, resizes to 64×64 with LANCZOS, applies gamma correction, and pushes the frame to the
matrix. Reconnects automatically if Volumio restarts.

Optional overlays, configured in the plugin UI:

- **Progress bar** — sits at the bottom edge; height, fill color, and track color are
  all configurable
- **Format badge** — shows codec/quality (`24/192`, `320K`, `DSD64`) in the top-left
  corner once per album, then clears

When nothing is playing, the matrix shows an idle image. Set a rotation interval to cycle
through a folder of photos instead.

## Photo manager

Manage idle images from a browser on the same network:

```
http://volumio.local:3018/photos
```

Upload, pick a fixed image, delete, or enable random rotation. Uploads are converted to
64×64 PNG by the bundled Pillow helper. SSH not required.

The photo manager binds to the local network with no authentication — it is designed for
use on a trusted home LAN, the same security model as Volumio itself.

For bulk imports from a Mac:

```bash
python3 tools/convert-idle-images.py ~/Pictures/source /tmp/converted --recursive
rsync -avz /tmp/converted/ volumio@<your-volumio-ip>:/data/INTERNAL/Vinyltron/idle-images/
```

## Architecture

```
Volumio pushState (Socket.io)
        │
        ▼
  volumio_client.py  ──►  vinyltron.py  ──►  display.py
  (reconnecting              (daemon)       (image pipeline)
   subscriber)                                    │
                                                  ▼
                                        rpi-rgb-led-matrix
                                        (C lib + Python bindings)
                                                  │
                                                  ▼
                                        64×64 HUB75E panel
```

## Dev tools

`deploy.sh` — rsync source to a Pi via SSH; development shortcut, not the normal install path  
`dev-install-plugin.sh` — build and push the plugin zip to a Pi for iterative testing

## Docs

- [Engineering spec](docs/engineering-spec.md)
- [Bill of materials](docs/bom.md)
- [Hardware notes](docs/hardware-notes.md)
- [Test procedure](docs/test-procedure.md)
- [Release process](docs/release.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](CHANGELOG.md)
