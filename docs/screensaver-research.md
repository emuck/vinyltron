# Screensaver Research

Status: Brian's Brain MVP implemented on `feature/screensaver-research`.

For user-facing behavior, see [screensavers.md](screensavers.md). For the browser preview
tool, see [matrix-simulator.md](matrix-simulator.md).

Vinyltron's current fallback modes are static-image based: built-in image, selected folder
image, and random folder image. A screensaver mode would make fallback display active
without changing the core Volumio album-art behavior.

The first candidate should be **Brian's Brain** because it is visually alive on a 64x64
matrix, cheap to compute, and has a strong neon-circuit-board look that fits the project.

## Product Shape

Screensavers should be an alternative idle/fallback mode, not a separate top-level feature.

User-facing model:

- **Idle Mode = Built-in Idle Image**
- **Idle Mode = Selected Folder Image**
- **Idle Mode = Random Folder Image**
- **Idle Mode = Screensaver: Brian's Brain**

The screensaver should run whenever Vinyltron would otherwise show fallback art:

- stopped playback after the existing fallback debounce
- startup fallback
- scheduled display-on idle state
- active playback with Volumio artwork disabled, if the user deliberately wants idle art
  behind overlays
- album-art fetch failure, as the fallback background for progress/format overlays

It should stop immediately when:

- Volumio artwork is available and enabled
- display power/schedule turns the matrix off
- the daemon shuts down or reloads config
- hardware settings trigger a service restart

## Brian's Brain

Brian's Brain is a three-state cellular automaton:

| State | Meaning | Next state |
|---|---|---|
| `0` | Dead/off | Ready only when exactly two ready neighbors exist |
| `1` | Ready/on | Dying |
| `2` | Dying/trail | Dead |

For each frame:

1. Count the eight neighboring cells whose current state is `1`.
2. A `1` cell becomes `2`.
3. A `2` cell becomes `0`.
4. A `0` cell becomes `1` only when exactly two neighbors are `1`.

Visual mapping:

- `0`: black
- `1`: bright electric color, for example cyan, blue, green, or magenta
- `2`: dim trail color, for example amber, red, violet, or deep blue

The effect is organic, fast-moving, and circuit-like. It is more useful as a display than
Conway's Game of Life because it tends not to settle into mostly static islands.

## Implementation Notes

Do not add NumPy for the first implementation. A 64x64 grid is only 4096 cells, and the Pi
3B can handle a bytearray-based pure-Python automaton at useful screensaver frame rates.
Adding NumPy would make install heavier, increase build risk on Bookworm/armhf, and add a
large dependency for a tiny grid.

MVP internals:

- Add a small `screensavers.py` module with a `BriansBrain` class.
- Store current and next state as `bytearray(4096)`.
- Use toroidal wrapping so edge cells connect across borders; this avoids dead borders.
- Precompute neighbor index lists once at startup:
  - `neighbors[i] = (n0, n1, ..., n7)`
  - frame update loops over `range(4096)` and indexes that table
- Render to an RGB bytearray and build a PIL image with `Image.frombytes('RGB', (64, 64), bytes(buffer))`.
- Reuse the existing `Display._render()` path so progress and format overlays still work.
- Use the existing matrix `SwapOnVSync` path. Vinyltron already uses the matrix library's
  frame canvas, so this preserves double-buffered output.

Avoid per-frame:

- `sin()` / `cos()` calls
- filesystem reads
- PIL resizing
- allocation-heavy Python lists
- random reseeding every frame

Implemented options:

```toml
[screensaver]
palette = "cyan_amber"
fps = 12
density = 0.22
seed = ""
```

For the UI, keep MVP options sparse:

- Idle Mode
- Screensaver Palette
- Screensaver Speed

Do not expose density/seed unless there is a clear user need.

## Where It Fits In The Current Code

Current flow:

- `vinyltron.py` decides when fallback should be visible.
- `display.py` chooses and renders the fallback image.
- `plugin/index.js` maps Volumio UI settings to `config.toml`.

Implemented flow:

- `vinyltron.py` owns timer lifecycle for an active fallback animation.
- `display.py` owns rendering a supplied screensaver frame as the current fallback image.
- `screensavers.py` owns automaton state and frame generation.
- `plugin/index.js` owns UI validation and config patching.

Concrete integration points:

- Calls that previously showed fallback directly now go through
  `_show_or_start_fallback_locked(status)`.
- If fallback mode is an image mode, keep current behavior.
- If fallback mode is a screensaver, render one frame immediately and schedule repeated
  frames with a timer.
- Cancel the screensaver timer anywhere idle rotation is currently cancelled:
  playback artwork arrival, config reload, display off, shutdown, and hardware restart.

The screensaver timer should be separate from random-folder rotation. Random-folder mode is
slow image rotation; screensaver mode is frame animation.

## Performance Notes

Target frame rate should be modest. A 64x64 matrix does not need 60 FPS.

Good defaults:

- 10-12 FPS for organic motion
- cap UI selection around 5, 8, 12, 16, 20 FPS
- log a warning and clamp invalid values

Pure Python loops are acceptable at this size if they avoid per-cell object churn. If
profiling on the Pi 3B shows missed frames, optimize in this order:

1. Precompute neighbor indexes.
2. Use local variables inside the update loop.
3. Keep state in `bytearray`.
4. Render with precomputed RGB triples.
5. Only then consider optional NumPy.

## Other Candidate Screensavers

Brian's Brain should be the first implementation. Other ideas worth exploring later:

- **Cyclic cellular automata**: color-wheel waves, very cheap and highly animated.
- **Langton's Ant variants**: iconic, but can look sparse on a 64x64 display until it warms up.
- **Sine plasma**: classic demoscene look; use precomputed sine lookup tables.
- **Reaction-diffusion inspired pattern**: visually strong, but likely too heavy unless
  simplified aggressively.
- **Orbit trails / Lissajous particles**: elegant, deterministic, and cheap with LUTs.

## MVP Acceptance Criteria

- Screensaver appears only when fallback would appear.
- Album art immediately interrupts it.
- Display off and schedule off stop it cleanly.
- Config reload stops old animation and starts the new selected fallback behavior.
- No new compiled dependency.
- Static validation still passes.
- No hardware test required for research branch, but final merge should be checked on real
  Pi hardware because animation cadence and LED scan timing are subjective.
