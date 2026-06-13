# Troubleshooting

This guide covers user-visible failures after Vinyltron is installed. For hardware parts,
power, Bonnet jumpers, and direct matrix checks, see [hardware.md](hardware.md).

## Photo Manager Does Not Load

The photo manager defaults to:

```text
http://volumio.local:3018/photos
```

It is available only on the local network and has no authentication. It is intended for a
trusted home LAN.

If the default port is already used by another service on the Pi:

- The **Photo Manager** field in Vinyltron Settings shows an unavailable-port message.
- Journald logs an error similar to `photo manager server failed: ... EADDRINUSE`.
- The matrix daemon can still run; only the photo manager is unavailable.

Fix:

1. Open `Plugins -> User Interface -> Vinyltron`.
2. Open the **Idle Image** section.
3. Set **Photo Manager Port** to an unused port from `1024` to `65535`.
4. Save.
5. Open the updated **Photo Manager** URL shown above the port field.

The photo manager restarts on the new port immediately. No full plugin restart is needed.

## Idle Images Do Not Appear

Check the configured idle folder:

```bash
ls -la /data/INTERNAL/Vinyltron/idle-images
```

Expected behavior:

- **Built-in Idle Image** uses the bundled `assets/idle.png`.
- **Selected Folder Image** uses the selected image from the configured folder.
- **Random Folder Image** chooses a supported image from the configured folder when the
  display enters idle state.
- **Screensaver** animates the selected generated display instead of loading an image file.
- Empty folders, missing selected files, and corrupt files fall back to `assets/idle.png`.

Useful logs:

```bash
journalctl -u vinyltron -n 200 --no-pager
```

Look for:

- `Config startup:` or `Config reload:` showing `fallback_mode`, `fallback_folder`,
  `fallback_selected`, and `volumio_artwork_enabled`
- `Loaded idle image ...`
- `Could not load idle image ...`

## Photo Uploads Fail

The web photo manager writes uploads to a temporary file, calls the bundled
`photo_upload_convert.py` helper, and stores only an optimized 64x64 PNG in the idle
folder.

HEIC/HEIF uploads use `heif-convert` from `libheif-examples`. `install.sh` installs that
tool from `bookworm-backports` when available; if backports was unreachable during
install, HEIC uploads fail with a conversion error while JPEG/PNG uploads still work.
Check the service log for the exact converter error:

```bash
journalctl -u vinyltron -n 100 --no-pager
which heif-convert
heif-convert --version
```

As a fallback, use camera/photo export settings that produce JPEG, or convert photos
before copying them to Volumio:

```bash
python3 tools/convert-idle-images.py "$HOME/Pictures/source" /tmp/vinyltron-idle --recursive
rsync -avz /tmp/vinyltron-idle/ volumio@<your-volumio-ip>:/data/INTERNAL/Vinyltron/idle-images/
```

## Progress Or Format Overlay Does Not Appear

Open Vinyltron Settings and check:

- **Progress Height** is greater than `0` if you want the progress strip.
- **Format Overlay** is enabled if you want the compact format text.
- **Format Duration** is long enough to see after a new album starts.

Useful config and logs:

```bash
cat /data/configuration/user_interface/vinyltron/config.toml
journalctl -u vinyltron -n 200 --no-pager
```

Look for:

- `[overlays] progress_bar_height`
- `[overlays] format_badge`
- `[overlays] badge_duration`
- `Volumio format:`
- `Format overlay:`

The format label appears once per album, not once per track, so track changes within the
same album may not show a new badge.

## Matrix Is Blank

First check hardware:

- Matrix power supply is on and polarity is correct.
- HUB75 ribbon orientation is correct.
- Bonnet is fully seated on the Pi header.
- Bonnet E-address jumper is closed for 64-row panels, if using the Bonnet.
- GPIO4-to-GPIO18 quality jumper is installed if using **Matrix Mapping = Bonnet PWM**.

If using the Bonnet without the quality jumper, set **Matrix Mapping = Bonnet** instead.
If using direct GPIO wiring, set **Matrix Mapping = Direct GPIO** and expect more flicker
than the Bonnet path.

If the matrix library demo works but Vinyltron does not, check:

```bash
systemctl status vinyltron --no-pager
journalctl -u vinyltron -n 200 --no-pager
```

## Onboard Or HDMI Audio Is Missing After Uninstall

This is expected if Vinyltron configured boot files for matrix PWM. Uninstall intentionally
does not restore onboard/HDMI audio, because doing so would make GPIO18/PWM unavailable for
the matrix.

To restore onboard audio, copy the original boot-file backups back and reboot:

```bash
sudo cp /boot/cmdline.txt.vinyltron-orig /boot/cmdline.txt
sudo cp /boot/userconfig.txt.vinyltron-orig /boot/userconfig.txt
sudo reboot
```
