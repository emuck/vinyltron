# Release Process

Vinyltron uses lightweight semantic versioning while it is still under active hardware
and plugin development.

## Version Sources

Keep these in sync for every release:

- `VERSION` - daemon version logged at startup.
- `plugin/package.json` - Volumio plugin package version.
- `plugin/package.json` `volumio_info.changelog` - short store-facing summary.
- `CHANGELOG.md` - human-readable release notes.
- Git tag - use `vX.Y.Z`.

## Checklist

1. Decide the next version.
2. Update `VERSION`.
3. Update `plugin/package.json` `version`.
4. Update `plugin/package.json` `volumio_info.changelog`.
5. Update `CHANGELOG.md`.
6. Run validation (also enforced by `.github/workflows/validate.yml` on every push/PR):
   ```bash
   python3 -m py_compile *.py tools/*.py
   python3 -m json.tool plugin/UIConfig.json
   python3 -m json.tool plugin/config.json
   node -c plugin/index.js
   bash -n plugin/install.sh plugin/uninstall.sh dev-install-plugin.sh tools/build-volumio-plugin.sh tools/install-volumio-plugin-zip.sh
   python3 -c "import tomllib; tomllib.load(open('config.toml','rb')); print('config.toml OK')"
   ./tools/build-volumio-plugin.sh
   git diff --check
   ```
   `bash -n` only checks syntax — it won't catch dash incompatibilities (e.g.
   `set -o pipefail`) in `install.sh`/`uninstall.sh`, which Volumio runs via `/bin/sh`
   (dash). If you change either script, test it on a real Volumio install.
7. Commit the release changes.
8. Tag the release:
   ```bash
   git tag -a vX.Y.Z -m "Vinyltron vX.Y.Z"
   git push origin main
   git push origin vX.Y.Z
   ```

## Volumio Submission Notes

For public Volumio submission, the plugin source should be submitted through the current
Volumio plugin source repository flow. The current Bookworm plugin source repo requires a
version bump in `package.json` for every plugin update and a new submission / pull request.

Do not commit generated plugin zip files or `node_modules`.

For a release-style local package that includes `node_modules`, run:
```bash
./tools/build-volumio-plugin.sh --with-node-modules
```

The default build omits `node_modules` so package layout can be validated without network
access. The release-style package should be tested through Volumio's plugin installer:
```bash
./tools/install-volumio-plugin-zip.sh volumio.local dist/vinyltron.zip
```
