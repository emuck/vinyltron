# vinyltron

Real-time album art display for a home audio system. A 64×64 HUB75 RGB LED matrix
driven by a Raspberry Pi 3B. Launched with Volumio 3.x as the source; designed to
support additional sources (Roon, Spotify, etc.) over time.

## Hardware

| Component | Part | Source |
|---|---|---|
| Display | 64×64 RGB LED Matrix, P3, 192×192mm | Amazon (~$37) |
| Interface | Adafruit RGB Matrix Bonnet (#3211) | Adafruit ($14.95) |
| Matrix PSU | 5V 4A switching supply (separate from Pi rail) | Amazon (~$12) |
| Host | Raspberry Pi 3B running Volumio 3.x | — |

Panel connects via HUB75E interface. The Bonnet handles 3.3V→5V level shifting
(74AHCT245). Matrix power is fully separate from the Pi's 5V rail.

## Architecture

```
Volumio pushState (Socket.io)
        │
        ▼
  volumio_client.py  ──►  vinyltron.py (daemon)  ──►  display.py
  (reconnecting              (orchestrator)         (image pipeline)
   subscriber)                                           │
                                                         ▼
                                               rpi-rgb-led-matrix
                                               (C lib + Python bindings)
                                                         │
                                                         ▼
                                               64×64 HUB75E panel
```

**Image pipeline:** fetch albumart → LANCZOS resize to 64×64 → gamma correction → push frame to matrix.

## Pi 3B Configuration

- `dtparam=audio=off` in `/boot/config.txt` (PWM conflict with HUB75 OE# on GPIO 18)
- rpi-rgb-led-matrix flag: `--led-slowdown-gpio=2`
- HUB75E E-address solder jumper on Bonnet must be closed for 64-row support

## Status

| Phase | Description | Status |
|---|---|---|
| 1 | Bill of Materials | ✅ Complete |
| — | Hardware assembled, display verified end-to-end | ✅ Complete |
| — | Core daemon (album art display, Socket.io, reconnect) | ✅ Working |
| — | Adafruit Bonnet #3211 (level shifting / flicker fix) | 🚚 On order |
| 2 | systemd service, idle image, SIGHUP reload | 🔲 In progress |
| 3 | Overlays (progress bar, format badge) + Volumio plugin | 🔲 Pending |

## Docs

- [Engineering Spec](docs/engineering-spec.md)
- [Bill of Materials](docs/bom.md)
- [Features & Roadmap](docs/features.md)
- [Test Procedure](docs/test-procedure.md)
