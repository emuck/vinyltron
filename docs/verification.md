# Verification Results

Vinyltron hardware and functional testing has been completed on real Raspberry Pi and
Volumio hardware. This document records what was verified; it is not a request to rerun
hardware tests.

## Platforms

- Raspberry Pi 3B with 64x64 HUB75E panel and Adafruit RGB Matrix Bonnet
- Raspberry Pi 5 software-pulse behavior
- Volumio 4 / Bookworm plugin install path
- Legacy Volumio 3 / Buster development baseline

## Completed Acceptance Coverage

- [x] Install from release-style plugin zip
- [x] Update from an existing plugin install
- [x] Uninstall from Volumio plugin manager
- [x] Reinstall after uninstall
- [x] `rgbmatrix` builds and imports on-device
- [x] `vinyltron` systemd service starts, stops, restarts, reloads, and shuts down cleanly
- [x] Playback state handling: play, pause, stop, reboot, and Volumio reconnect
- [x] Album art rendering on the 64x64 matrix
- [x] Idle image fallback after stop debounce
- [x] Selected idle image mode
- [x] Random folder idle image mode and rotation interval
- [x] Photo manager upload, preview, select, random mode, delete, and JSON image list
- [x] Bulk idle-photo conversion workflow
- [x] Progress strip overlay
- [x] Format overlay with Tom Thumb, Tiny5, and Spleen font choices
- [x] Plugin settings save and round-trip behavior
- [x] Boot-file configuration for `snd_bcm2835` / GPIO18 PWM conflict
- [x] Pi 5 daemon behavior with hardware-pulse mode forced off

## Important Pi 5 Scope Note

Pi 5 testing confirmed install, Python binding import, daemon startup, Volumio connection,
and clean shutdown in software-pulse mode. Actual HUB75 panel rendering on Pi 5 remains
untested because the Bonnet mounting stack was not validated on that hardware.

## Historical Test Procedure

The original manual smoke-test flow included:

- Direct GPIO wiring checks
- `rpi-rgb-led-matrix` C demo checks
- Python binding import checks
- Volumio Socket.IO pushState checks
- Overlay behavior checks
- Idle image and photo manager checks

Those details were useful during bring-up, but the public user path is now the plugin
install flow documented in [install.md](install.md).
