# Release Process

Vinyltron uses lightweight semantic versioning while it is still under active hardware
and plugin development.

## Version Sources

Keep these in sync for every release:

- `VERSION` - daemon version logged at startup.
- `plugin/package.json` - Volumio plugin package version.
- `plugin/package.json` `volumio_info.changelog` - short store-facing summary.
- `CHANGELOG.md` - human-readable release notes.
- Git tag - use `vinyltron-vX.Y.Z` because this project lives in a larger repository.

## Checklist

1. Decide the next version.
2. Update `VERSION`.
3. Update `plugin/package.json` `version`.
4. Update `plugin/package.json` `volumio_info.changelog`.
5. Update `CHANGELOG.md`.
6. Run validation:
   ```bash
   python3 -m py_compile display.py vinyltron.py volumio_client.py test_matrix.py
   python3 -m json.tool plugin/UIConfig.json
   python3 -m json.tool plugin/config.json
   node -c plugin/index.js
   bash -n plugin/install.sh plugin/uninstall.sh dev-install-plugin.sh tools/build-volumio-plugin.sh
   python3 -c "import tomllib; tomllib.load(open('config.toml','rb')); print('config.toml OK')"
   ./tools/build-volumio-plugin.sh
   git diff --check
   ```
7. Commit the release changes.
8. Tag the release:
   ```bash
   git tag -a vinyltron-vX.Y.Z -m "Vinyltron vX.Y.Z"
   git push origin main
   git push origin vinyltron-vX.Y.Z
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
access.
