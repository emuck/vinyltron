# Roadmap: Public Release → Volumio Plugin Store

## M1 — Public Launch

_Repo is clean and ready to flip to public._

- [x] MIT license added
- [x] Home network IP scrubbed from docs
- [x] README updated — plugin install as the lead path, legacy scripts noted as dev tools
- [x] Stale branch reference in `next-steps.md` removed or updated
- [ ] Repo flipped to public on GitHub

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

_End-to-end verified on Volumio 3 / Buster hardware._

- [ ] Install from zip on a fresh Volumio Bookworm install
- [ ] All four UI settings sections save and round-trip correctly to `config.toml`
- [x] Service lifecycle: start, stop, reload (SIGHUP), restart all behave correctly
- [x] Photo manager: upload, preview, select, delete, random mode
- [x] Uninstall cleans up cleanly; reinstall works from scratch

---

## M4 — Bookworm / Volumio 4 Compatibility

_Plugin targets the current platform._

- [ ] `package.json` architectures updated to Bookworm format (`armhf`, `os: ["bookworm"]`, `engines: {node: ">=20", volumio: ">=4"}`)
- [ ] `index.js` verified compatible with Node ≥ 20
- [ ] `plugin/install.sh` and `plugin/uninstall.sh` verified against Bookworm paths
- [ ] `plugin/UIConfig.json` reviewed against current Volumio UI framework

---

## M5 — Documentation Polish

_Docs are accurate, sparse, and useful to a new user finding the repo cold._

- [ ] README is the single entry point: quick start via plugin, hardware wiring, architecture diagram
- [x] `docs/next-steps.md` converted from dev log to forward-looking notes or removed
- [ ] `docs/features.md` trimmed to what is shipped; future ideas removed or marked clearly
- [ ] `CHANGELOG.md` current through store submission version
- [ ] Internal dev scripts (`deploy.sh`, `dev-install-plugin.sh`) have one-line headers explaining their purpose

---

## M6 — Plugin Store Submission

_Plugin is live in the Volumio beta channel._

- [ ] Fork `volumio/volumio-plugins-sources-bookworm`
- [ ] Add plugin to fork under `user_interface/vinyltron/`
- [ ] Run `volumio plugin submit` from a running Volumio device
- [ ] PR opened; submission checklist completed
- [ ] Respond to Volumio team review feedback
- [ ] Plugin live in beta channel
