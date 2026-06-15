# Changelog

All notable Vinyltron changes are tracked here. Versions should match `VERSION`,
`plugin/package.json`, and git tags using the `vX.Y.Z` format.

## [Unreleased]

## [0.2.10] - 2026-06-14

- Added a new `weather` fallback/idle mode: a 64x64 pixel-art display showing current
  conditions (temperature, condition icon, H/L) plus a secondary metric (humidity, wind,
  or an animated AQI glyph), with moon-phase rendering at night. The Settings UI gained a
  Weather section (location, units, refresh interval, night icon, secondary metric, fps).
- Live weather data is fetched from Open-Meteo in a background thread (`WeatherService`),
  with periodic refresh and retry/staleness handling. Without coordinates configured, or
  with `source = mock`, the display falls back to a mock renderer driven by
  `mock_condition`/`mock_night`/`mock_moon_phase` in `config.toml`.
- The AQI glyph is color-coded by EPA AQI tier and has a slow breathing brighten/dim cycle
  (~1.5s brighten / 3s dim) when `secondary_metric = aqi`.
- `tools/matrix-sim.py` gained a weather engine preview with controls for condition,
  night/moon phase, and secondary metric, for tuning the renderer without hardware.
- Fixed `BIG_DIGITS` missing a `-` glyph, which caused negative current temperatures
  (e.g. -12°) to render without the minus sign.
- Fixed `WeatherService._fetch()` to tolerate a failed AQI sub-request: previously an
  unreachable air-quality endpoint discarded an otherwise-successful forecast fetch,
  leaving the renderer stuck on mock data.
- Added `docs/weather.md` describing the mock/live behavior, AQI gating, and simulator
  usage.

## [0.2.9] - 2026-06-13

- Added a fourth screensaver engine: Reaction-Diffusion, a Gray-Scott two-chemical
  simulation that produces slowly evolving coral/spot/worm patterns. Runs on a
  downscaled grid (32x32 by default, `grid_scale`) bilinear-upscaled to the panel size,
  with color mapped through the selected palette. Advanced tuning (`feed`, `kill`,
  `grid_scale`) is config-file-only, matching the other engines' advanced parameters.
  Prototyped and tuned in `tools/matrix-sim.py` before wiring into `vinyltron.py` and the
  plugin Settings UI.

## [0.2.8] - 2026-06-13

- Fixed `tools/install-volumio-plugin-zip.sh` and `docs/install.md` to restart the
  `volumio` service (in addition to `vinyltron`) after `volumio plugin update`/`install`.
  `volumio` runs the plugin's settings UI code (`index.js`), and `plugin update` does not
  reload it into the running process — so after an update, Screensaver settings saves kept
  validating against the *previous* version's `_validScreensaverEngine` and silently fell
  back to Brian's Brain no matter what was selected.

## [0.2.7] - 2026-06-13

- Added animated screensaver fallback modes with a dedicated Screensaver settings section,
  generic engine/palette/speed/reset controls, and advanced tuning kept in `config.toml`.
  Engines currently include Brian's Brain, multi-ant Langton's Ant, and a rotating Chaos
  Game / Sierpinski-style fractal.
- The idle display now starts after 5 minutes even if Volumio's `/status` endpoint never
  reports `ready`, instead of leaving the matrix uninitialized indefinitely.
- `tools/matrix-sim.py`'s Speed control is now a Slow/Medium/Fast dropdown (4/6/10 fps),
  matching the plugin's Screensaver "Speed" setting exactly. Its Chaos Game Rotation Speed
  slider range was also widened from -8..8 to -16..16 to match the engine's actual clamp.
- Added HEIC/HEIF support to the photo upload converter via `heif-convert`. Previously,
  uploading an iPhone-format `.HEIC` photo failed with "Could not convert image"
  (`PIL.UnidentifiedImageError`), since Pillow has no built-in HEIF decoder.
- `plugin/install.sh` now installs `libheif-examples`/`libheif1` 1.19.7 from
  `bookworm-backports` (Bookworm's default 1.15.1 rejects HEIC photos from iPhone 15 Pro+ /
  iOS 18 with "Too many auxiliary image references", an HDR gain-map structure fixed
  upstream in libheif 1.18.0). A from-source build was tried first but ruled out: a Pi 3B
  has no free memory for the compiler and no usable swap (the overlay root filesystem
  can't host a swapfile).
- Fixed `tools/install-volumio-plugin-zip.sh` to restart the `vinyltron` service after
  `volumio plugin install`/`update`. Volumio's `plugin update` path doesn't restart the
  daemon, so it kept running with stale code and a stale working directory after every
  reinstall — this is why `assets/idle.png` failed to load with `No such file or
  directory` until the service was restarted manually.

## [0.2.6] - 2026-06-12

- Corrected install docs: Volumio's web UI no longer has a plugin-zip "Manual Install"
  option. Installing or updating Vinyltron requires SSH and `volumio plugin install`
  (README.md, docs/install.md).
- Fixed `tools/install-volumio-plugin-zip.sh` to run `volumio plugin update` instead of
  `volumio plugin install` when Vinyltron is already installed — `install` fails with
  `Plugin vinyltron already exists` on a reinstall. Documented the same `install` vs
  `update` distinction in docs/install.md.
- Added a configurable Photo Manager port in the plugin settings and an in-UI warning when
  the manager cannot bind the selected port.
- Reworked public documentation around a product-first README, canonical install,
  hardware, troubleshooting, and verification guides.
- Documented the longer-term turntable listening mode vision behind the Vinyltron name.
- Replaced the built-in idle image with new "July 1937 VINYLTRON" artwork. The previous
  eye/flame idle image moves to `assets/idle-images/vinyltron-eye.png` and joins the
  random photo pool.
- `saveIdle`/`saveDisplay`/`saveHardware`/`toggleDisplay` in `plugin/index.js` now guard
  against a missing UI payload.

## [0.2.5] - 2026-06-12

- Plugin lifecycle/robustness fixes from a pre-submission audit:
  `onRestart`/`onInstall`/`onUninstall`/`setUIConfig` no-ops added;
  `onStart`/`onRestart` now reject if `systemctl` fails, per Volumio convention;
  photo manager listen failures are surfaced via `getAdditionalConf`;
  `saveDisplay`/`saveHardware` guard against malformed UI payloads; photo
  upload staging errors return a JSON 500 instead of throwing.
- `install.sh` now also backs up `/boot/userconfig.txt` as
  `userconfig.txt.vinyltron-orig` before its first edit.
- Clarified that uninstall intentionally leaves onboard/HDMI audio disabled
  (for matrix PWM) and documented how to restore it from the `.vinyltron-orig`
  backups.
- Moved the manual install walkthrough to `docs/install.md`.
- Added MIT/provenance headers to the bundled `tools/matrix-build/` helpers.

## [0.2.4] - 2026-06-11

- `install.sh` now configures `/boot/userconfig.txt` (`dtparam=audio=off`) and
  `/boot/cmdline.txt` (removes `snd_bcm2835.enable_hdmi=1`/`enable_headphones=1`,
  appends `module_blacklist=snd_bcm2835 modprobe.blacklist=snd_bcm2835`)
  automatically and idempotently, so hardware-pulse PWM mode with the Bonnet works
  out of the box without any manual SSH setup. Prints a reboot reminder if either
  file changed; originals are saved as `cmdline.txt.vinyltron-orig` and
  `userconfig.txt.vinyltron-orig`.
- The systemd service now sets `Environment=PYTHONDONTWRITEBYTECODE=1`, so the
  root-running daemon no longer leaves `__pycache__/*.pyc` behind in the plugin
  directory. Previously this could make `/bin/mv` fail with "Directory not empty"
  during the next `volumio plugin update`, hanging the update indefinitely.
- `display.py` now detects Raspberry Pi 5 (`/proc/device-tree/model`) and forces
  `disable_hardware_pulsing=True`, regardless of config. On this Pi 5, hardware-pulse
  mode (`disable_hardware_pulsing=False`) causes rpi-rgb-led-matrix's PWM init to hang
  (the pinned library predates RP1 GPIO support), which busy-spins and prevents the
  daemon from responding to SIGTERM — `systemctl stop`/`restart`/uninstall/update would
  hang for 90s and require SIGKILL. Software-pulse mode is unaffected and shuts down
  cleanly in ~1s.

## [0.2.3] - 2026-06-11

- `install.sh` now builds the rpi-rgb-led-matrix C library and Python bindings from
  source automatically on first install, downloading the pinned commit
  (`e947417fff9042b3ea173542be09490acab069f7`) as a tarball and building the bundled
  `matrix-build/` Cython extension. Removes the manual SSH prerequisite steps entirely —
  installing the plugin zip is now sufficient.
- `install.sh` always prints `plugininstallend`, even on failure, and removes the plugin
  folder on a failed install (matching Volumio plugin manager conventions).
- `install.sh` now uses `set -e` instead of `set -eo pipefail` and avoids piping into
  `tar`, since Volumio runs the script with `sh` (dash), which doesn't support
  `pipefail` and was causing every install to fail instantly.
- `tools/build-volumio-plugin.sh` bundles `tools/matrix-build/` into the plugin package
  as `vinyltron/matrix-build/`.

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
