# Roadmap: Public Release → Volumio Plugin Store

## M1 — Public Launch

_Privacy and licensing checks are done; the repo is ready for the public-launch checklist
below. End-to-end Bookworm testing (M4) remains a known follow-up after launch._

- [x] MIT license added
- [x] Home network IP scrubbed from docs
- [x] README updated — plugin install as the lead path, legacy scripts noted as dev tools
- [x] Stale branch reference in `next-steps.md` removed or updated
- [x] Repo flipped to public on GitHub

---

## M2 — Code Audit

_All source files reviewed for clarity, correctness, and dead code._

- [x] `vinyltron.py` — orchestrator logic, state machine, SIGHUP handling
- [x] `display.py` — image pipeline, gamma, overlays, schedule
- [x] `volumio_client.py` — Socket.io reconnect loop, state parsing
- [x] `photo_upload_convert.py` — upload pipeline, EXIF handling
- [x] `plugin/index.js` — plugin lifecycle, photo manager server, TOML patching
- [x] Comments audit: keep only where the *why* is non-obvious; remove the rest
- [x] No dead code, no TODO comments, no unused config keys

---

## M3 — Plugin Integration Test

_End-to-end verified on Volumio 3 / Buster hardware, and Volumio 4 / Bookworm
(see Known Issues)._

- [x] Install from zip on a fresh Volumio Bookworm install
- [x] All four UI settings sections save and round-trip correctly to `config.toml`
- [x] Service lifecycle: start, stop, reload (SIGHUP), restart all behave correctly
- [x] Photo manager: upload, preview, select, delete, random mode
- [x] Uninstall cleans up cleanly; reinstall works from scratch

---

## M4 — Bookworm / Volumio 4 Compatibility

_Plugin targets the current platform._

- [x] `package.json` architectures updated to Bookworm format (`armhf`, `os: ["bookworm"]`, `engines: {node: ">=20", volumio: ">=4"}`)
- [x] `index.js` verified compatible with Node ≥ 20 — replaced deprecated `url.parse()` with `new URL()`
- [x] `plugin/install.sh` updated for Bookworm pip behavior (PEP 668 / `--break-system-packages`)
- [x] `plugin/UIConfig.json` reviewed against current Volumio UI framework — no changes needed
- [x] End-to-end test on Volumio 4 / Bookworm hardware

---

## Known Issues

- **Bookworm hardware-pulse flicker** (confirmed 2026-06-10): On Volumio 4 / Bookworm,
  `snd_bcm2835` remains loaded even with `dtparam=audio=off` in `userconfig.txt` —
  Volumio's custom `volumio.initrd` isn't rebuilt by `update-initramfs`, so the usual
  blacklist-and-rebuild fix doesn't apply. The daemon detects this at startup and
  falls back to `disable_hardware_pulsing = True` (`display.py`), so the plugin
  installs and runs correctly, but with noticeably more flicker than on Buster.
  Production displays should stay on Volumio 3 / Buster until this is fixed —
  either upstream in Volumio's initramfs tooling, or via a safe in-place initramfs
  patch. See `docs/engineering-spec.md` for details.

---

## M5 — Documentation Polish

_Docs are accurate, sparse, and useful to a new user finding the repo cold._

- [x] README is the single entry point: quick start via plugin, hardware wiring, architecture diagram
- [x] `docs/next-steps.md` converted from dev log to forward-looking notes or removed
- [x] `docs/features.md` removed — content folded into engineering-spec.md
- [x] `CHANGELOG.md` current through store submission version
- [x] Internal dev scripts (`deploy.sh`, `dev-install-plugin.sh`) have one-line headers explaining their purpose

---

## M6 — Plugin Store Submission

_Plugin is live in the Volumio beta channel._

- [ ] Fork `volumio/volumio-plugins-sources-bookworm`
- [ ] Add plugin to fork under `user_interface/vinyltron/`
- [ ] Run `volumio plugin submit` from a running Volumio device
- [ ] PR opened; submission checklist completed
- [ ] Respond to Volumio team review feedback
- [ ] Plugin live in beta channel
