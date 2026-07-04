# Roadmap: Public Release → Volumio Plugin Store

## M1 — Public Launch

_Privacy and licensing checks are done; the repo is ready for the public-launch checklist
below. End-to-end Bookworm testing (M4) is complete._

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

_End-to-end verified on Volumio 3 / Buster hardware and Volumio 4 / Bookworm._

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
- [x] Hardware-pulse mode verified on Volumio 4 / Bookworm by disabling `snd_bcm2835`
  with `/boot/userconfig.txt` and `/boot/cmdline.txt` boot args; see
  `docs/engineering-spec.md`.

---

## M5 — Documentation Polish

_Docs are accurate, sparse, and useful to a new user finding the repo cold._

- [x] README is the single entry point: quick start via plugin, hardware wiring, architecture diagram
- [x] `docs/next-steps.md` converted from dev log to forward-looking notes or removed
- [x] `docs/features.md` removed — content folded into engineering-spec.md
- [x] `CHANGELOG.md` current through store submission version
- [x] Internal dev scripts (`deploy.sh`, `dev-install-plugin.sh`) have one-line headers explaining their purpose

---

## M6 — Plugin Store Submission ✓

_Goal: get the plugin live in the Volumio beta channel._

- [x] Fork `volumio/volumio-plugins-sources-bookworm`
- [x] Add plugin to fork under top-level `vinyltron/`
- [x] Run `volumio plugin submit` from a running Volumio device
- [x] PR opened; submission checklist completed
- [x] Respond to Volumio team review feedback
- [x] Plugin live in beta channel

---

## Future — Turntable Listening Mode

_The name Vinyltron points here._

The long-term idea is automatic artwork display for records and other analog sources:
put the needle down, let Vinyltron listen, identify the track, fetch the artwork, and show
it on the same matrix.

Possible flow:

```text
IDLE
  audio level rises above threshold for a few seconds
DETECTING
  capture short audio clip and send it to a recognition backend
MATCHED
  resolve artist/album/track metadata and fetch artwork
DISPLAYING
  keep showing artwork until a long silence suggests the record stopped or the side changed
IDLE
```

Open research items:

- [ ] Find a free, low-cost, or self-hostable Shazam-like recognition backend suitable for
      personal/home use
- [ ] Prototype USB microphone or line-input capture on the Pi without interfering with
      Volumio playback or the GPIO matrix timing
- [ ] Tune onset and silence detection so between-track gaps do not cause false lookups,
      but flipping a record side does
- [ ] Fetch artwork from a reliable source such as MusicBrainz / Cover Art Archive after a
      recognition match
- [ ] Decide whether this belongs inside the Volumio plugin or as a separate companion
      service feeding the same display daemon

UX goal: put needle on record, artwork appears a few seconds later, no app interaction.
