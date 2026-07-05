# Screensavers

Vinyltron can use an animated screensaver as the idle fallback instead of a static image.
Album art still wins: when Volumio provides artwork and artwork display is enabled, the
screensaver stops immediately and the matrix returns to album art.

## How To Enable

Open Vinyltron Settings and set:

- **Idle Mode**: `Screensaver`
- **Screensaver**: `Brian's Brain`, `Langton's Ant`, `Chaos Game`, `Reaction-Diffusion`, or `Lissajous`
- **Palette**: choose a color pair
- **Speed**: `Slow`, `Medium`, or `Fast`
- **Reset Interval**: seconds between random state resets, or `0` to disable

The screensaver appears anywhere Vinyltron would otherwise show fallback art:

- playback stopped after the normal debounce
- startup while idle
- scheduled display-on idle state
- album-art fetch failure
- playback with Volumio artwork disabled

During early service startup, Vinyltron keeps the matrix display uninitialized for every
idle fallback mode. It polls Volumio's local `/status` endpoint and only starts the idle
display after Volumio reports `ready` plus a short extra grace period. Playback artwork can
still initialize the matrix immediately. This keeps boot lighter while Volumio, networking,
and the web UI finish coming up. If `/status` never reports `ready`, Vinyltron starts the
idle display anyway after 5 minutes so the matrix doesn't stay blank indefinitely.

It stops on playback artwork, display off, config reload, service stop, and shutdown.

## Brian's Brain

**Brian's Brain** is a cellular automaton invented by Brian Silverman. It has a more
active, neon-circuit look than Conway's Game of Life, which makes it a good fit for a 64x64
LED matrix.

Each LED is one cell with three states:

| State | Display role | Next state |
|---|---|---|
| `Dead` | off / black | becomes `Ready` only with exactly two ready neighbors |
| `Ready` | bright live pixel | always becomes `Dying` |
| `Dying` | dim trail pixel | always becomes `Dead` |

Every frame counts the eight surrounding neighbors for each cell. Only neighbors in the
`Ready` state count. The update rules are:

1. `Ready -> Dying`
2. `Dying -> Dead`
3. `Dead -> Ready` when exactly two neighbors are `Ready`
4. all other `Dead` cells stay `Dead`

Vinyltron wraps the grid at the edges, so the left edge connects to the right edge and the
top edge connects to the bottom. That avoids dead borders and keeps patterns moving across
the whole matrix.

## Visual Design

Brian's Brain uses a two-color palette:

- `Ready`: bright electric color
- `Dying`: darker trail color
- `Dead`: black

Available palettes:

- `Cyan / Amber`
- `Green / Magenta`
- `Blue / Red`
- `White / Violet`

The result is a constantly moving pattern of sparks, trails, and branching structures. If
the automaton gets too quiet, Vinyltron reseeds it so the idle display does not burn down to
black during long listening sessions. The reset interval also forces a fresh random state
periodically, which helps if a run condenses into a less interesting pattern.

## Langton's Ant

Langton's Ant is a two-state cellular automaton with a moving agent. Vinyltron runs several
ants at once so their paths collide and keep changing instead of settling into a single
predictable highway.

Each ant follows simple rules:

1. On an off cell, turn right, switch the cell on, then move forward.
2. On an on cell, turn left, switch the cell off, then move forward.
3. At panel edges, wrap around to the opposite side.

Each ant uses a different color from the selected palette. The result is a neon trail maze:
mostly geometric, very lightweight, and visually distinct from Brian's Brain.

## Chaos Game

Chaos Game is a fractal generator. It starts with a point, repeatedly chooses one triangle
vertex at random, then moves halfway from the current point toward that vertex and lights
the new point. Random choices gradually reveal a structured Sierpinski-style triangle.

Vinyltron keeps it screensaver-like by rotating the triangle vertices and fading old
points. That makes the fractal breathe instead of settling into a static picture.

Advanced tuning controls how many random points are plotted per rendered frame, how quickly
older pixels fade, and how fast the triangle vertices rotate.

## Reaction-Diffusion (Gray-Scott)

Reaction-Diffusion runs the classic Gray-Scott two-chemical model: each cell holds
concentrations of chemicals U and V that diffuse into neighboring cells and react with each
other according to feed and kill rates. Starting from a few seeded patches, the simulation
settles into a self-sustaining pattern of spots, worms, or coral-like growth that never
fully repeats.

To keep this affordable on a Pi 3B, the simulation runs on a downscaled grid (32x32 by
default, `grid_scale = 2`) and the result is bilinear-upscaled to the panel size. The V
concentration is mapped through a color gradient using the selected palette, giving a
"lava lamp" look: dark background, glowing mid-tones, and bright highlights where the
reaction is most active.

Advanced tuning controls the feed rate, kill rate, and grid scale. Lower kill values tend
to produce faster-spreading "worm" patterns; higher values tend toward more static spots.

## Lissajous

Lissajous draws a parametric Lissajous figure — the path traced by a point whose x and y
coordinates follow independent sinusoidal oscillations at different frequencies. The default
frequency ratio is 3:2, producing a smooth three-lobed orbit. Older pixels fade out, leaving
a glowing trail that retains the figure's shape while the phase drifts slowly over time.

Because the figure is fully redrawn each frame from a parametric equation, there is no
random state to seed and no grid to reset — the pattern changes continuously via the phase
drift alone. Speed controls the drift rate; a slower setting extends the visible trail.

Advanced tuning controls the frequency ratio (`freq_a`, `freq_b`), trail fade rate, and
drift speed.

## Configuration Model

The Volumio plugin UI only exposes controls that make sense across screensavers:

- screensaver engine
- palette
- speed
- reset interval

Engine-specific tuning stays in the daemon config file for advanced users:

```toml
[display]
startup_delay_seconds = 5

[screensaver]
engine = "brians_brain"
palette = "cyan_amber"
fps = 6
reset_seconds = 300

# Advanced Brian's Brain tuning
density = 0.22

# Advanced Langton's Ant tuning
ant_count = 4
steps_per_frame = 96

# Advanced Chaos Game tuning
points_per_frame = 320
fade = 12
rotation_speed = 2

# Advanced Reaction-Diffusion (Gray-Scott) tuning
feed = 0.055
kill = 0.062
grid_scale = 2

seed = ""
```

The config file lives at:

```text
/data/configuration/user_interface/vinyltron/config.toml
```

`[display].startup_delay_seconds` is exposed in the plugin UI as **Startup Delay
(seconds)**. It is an extra grace period after Volumio's `/status` endpoint reports
`ready`, before any idle fallback mode starts the matrix. Set it to `0` to start the idle
display as soon as Volumio reports ready.

After editing the config over SSH, reload the daemon:

```bash
sudo systemctl reload vinyltron
```

## Performance

The implementation is deliberately small and Pi 3B-friendly:

- no NumPy
- no compiled dependency
- compact `bytearray` grids for automaton state
- precomputed neighbor indexes
- one RGB byte buffer per frame
- modest default speed: 6 FPS

The generated frame is handed to the same display path as album art and fallback images, so
gamma correction, overlays, and the matrix driver's double-buffered `SwapOnVSync` path still
apply.

## Simulator

Use the browser simulator to preview colors and motion before installing on hardware:

```bash
python3 tools/matrix-sim.py
```

Then open:

```text
http://127.0.0.1:8765
```

See [matrix-simulator.md](matrix-simulator.md) for details.
