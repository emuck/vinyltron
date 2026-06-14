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
- **Idle Mode = Screensaver**

Screensaver section model:

- **Screensaver = Brian's Brain**
- **Palette = Cyan / Amber**, etc.
- **Speed = Slow / Medium / Fast**
- **Reset Interval = seconds**, with `0` disabling periodic resets

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
[display]
startup_delay_seconds = 5

[screensaver]
engine = "brians_brain"
palette = "cyan_amber"
fps = 6
reset_seconds = 300
density = 0.22
ant_count = 4
steps_per_frame = 96
points_per_frame = 320
fade = 12
rotation_speed = 2
seed = ""
```

For the UI, keep options generic across screensaver engines:

- Screensaver
- Palette
- Speed
- Reset Interval

Keep engine-specific keys such as Brian's Brain `density`, Langton's Ant `ant_count` /
`steps_per_frame`, Chaos Game `points_per_frame` / `fade` / `rotation_speed`, or
deterministic `seed` out of the plugin UI unless there is a clear user need. Advanced users
can edit those keys directly in
`/data/configuration/user_interface/vinyltron/config.toml`.

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
- Before Volumio reports `ready`, leave the matrix uninitialized for all idle fallback
  modes.
- If fallback mode is an image mode, render the selected fallback after the startup gate.
- If fallback mode is a screensaver, render one frame after the startup gate and schedule
  repeated frames with a timer.
- Cancel the screensaver timer anywhere idle rotation is currently cancelled:
  playback artwork arrival, config reload, display off, shutdown, and hardware restart.

The screensaver timer should be separate from random-folder rotation. Random-folder mode is
slow image rotation; screensaver mode is frame animation.

## Performance Notes

Target frame rate should be modest. A 64x64 matrix does not need 60 FPS.

Good defaults:

- 6 FPS for Pi 3B safety; faster presets can be exposed for users who prefer motion over
  idle CPU headroom
- keep the matrix uninitialized during boot for idle fallback modes, wait for Volumio's
  `/status` endpoint to report `ready`, then apply a short `startup_delay_seconds` grace
  period before starting the idle display
- cap UI selection around low Pi-friendly presets such as 4, 6, and 10 FPS
- log a warning and clamp invalid values

Pure Python loops are acceptable at this size if they avoid per-cell object churn. If
profiling on the Pi 3B shows missed frames, optimize in this order:

1. Precompute neighbor indexes.
2. Use local variables inside the update loop.
3. Keep state in `bytearray`.
4. Render with precomputed RGB triples.
5. Only then consider optional NumPy.

## Other Candidate Screensavers

Brian's Brain, multi-ant Langton's Ant, and Chaos Game are implemented. Other ideas worth
exploring later:

- **Cyclic cellular automata**: color-wheel waves, very cheap and highly animated.
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
