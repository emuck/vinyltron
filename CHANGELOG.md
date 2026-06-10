# Changelog

All notable Vinyltron changes are tracked here. Versions should match `VERSION`,
`plugin/package.json`, and git tags using the `vX.Y.Z` format.

## [0.2.2] - 2026-06-10

- Fix Bookworm hardware-pulse flicker: `snd_bcm2835` was loading despite
  `dtparam=audio=off`, forcing software pulse timing. Documented the fix
  (`module_blacklist=snd_bcm2835 modprobe.blacklist=snd_bcm2835` in
  `/boot/cmdline.txt`) so `disable_hardware_pulsing = false` now works on
  Volumio 4 / Bookworm with the same quality as Buster.
- Add a runtime safety net in `display.py`: if `snd_bcm2835` is still loaded
  at startup, force `disable_hardware_pulsing = true` instead of letting
  rpi-rgb-led-matrix hard-exit.
- Install `libjpeg-dev`/`zlib1g-dev` in `plugin/install.sh` so Pillow can build
  from source on Bookworm's armv7l.

## [0.2.1] - 2026-06-09

- Fix `tools/build-volumio-plugin.sh` packaging `.git/` and `.claude/` into the plugin
  zip's bundled daemon directory.

## [0.2.0] - 2026-06-09

- Add a phone-friendly plugin photo manager for idle image upload, selection, random mode,
  and deletion.
- Add a bundled Python/Pillow upload converter that writes optimized 64x64 PNG idle images.
- Add an optional daily matrix power schedule for photo-frame use when idle.
- Treat zero-valued bitrate metadata as unknown instead of showing `0K`.
- Allow active Volumio playback artwork to override the idle/photo display schedule.
- Replace progress color dropdowns with free-text R,G,B inputs — any RGB color is now valid.
- Replace format badge duration dropdown with a typed seconds field.
- Target Bookworm / Volumio 4 (`armhf`, Node ≥ 20, `volumio >= 4`).
- Handle PEP 668 pip restriction on Python 3.11+ with `--break-system-packages`.

## [0.1.0] - 2026-05-27

Initial public-development baseline.

- Display Volumio album art on a 64x64 HUB75 RGB LED matrix.
- Add Volumio pushState integration with reconnect behavior.
- Add systemd service and SIGHUP runtime reload.
- Add progress bar overlay with configurable height and colors.
- Add compact format text overlay with Tom Thumb, Tiny5, and Spleen 5x8 font choices.
- Add Spotify, MP3/AAC/OGG, lossless, and DSD format labels.
- Add folder-based idle image selection and randomization.
- Add Volumio plugin settings UI for display, idle image, hardware, and power controls.
- Add runtime config/version logging for deployment diagnostics.
