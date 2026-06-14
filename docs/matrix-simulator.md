# Matrix Simulator

`tools/matrix-sim.py` is a local browser-based 64x64 LED matrix simulator. It is a
development tool for testing generated frames, colors, and animation behavior before
deploying to real HUB75 hardware.

It does not simulate electrical timing, panel scan artifacts, GPIO contention, or the
subjective brightness of the physical matrix. It does test the part of the pipeline where a
screensaver produces a 64x64 RGB frame and hands it off for display.

## Run

```bash
python3 tools/matrix-sim.py
```

Open:

```text
http://127.0.0.1:8765
```

Optional host/port:

```bash
python3 tools/matrix-sim.py --host 127.0.0.1 --port 8765
```

## What It Simulates

The simulator mirrors Vinyltron's display handoff boundary:

1. A screensaver engine generates a 64x64 RGB frame.
2. The simulator exposes that frame as raw RGB bytes from `/api/frame`.
3. The browser paints those bytes onto a 64x64 canvas scaled up with pixelated rendering.

That makes it useful for algorithm and palette work. The browser canvas plays the role of
the RGB matrix frame canvas; the real hardware path still uses `rgbmatrix.SetImage()` and
`SwapOnVSync()`.

The raw frame endpoint returns exactly:

```text
64 * 64 * 3 = 12288 bytes
```

## Current Controls

- **Engine**: `Brian's Brain`, `Langton's Ant`, `Chaos Game`, or `Reaction-Diffusion`
- **Palette**: color pair or gradient used by the selected engine
- **Speed**: `Slow` / `Medium` / `Fast` (4 / 6 / 10 fps), matching the plugin's Screensaver
  "Speed" setting; controls browser playback target
- **Density**: initial ready-cell density for Brian's Brain
- **Ant Count**: number of active ants for Langton's Ant
- **Steps Per Frame**: Langton's Ant simulation steps before each rendered frame
- **Points Per Frame**: Chaos Game random midpoint plots before each rendered frame
- **Fade**: Chaos Game per-frame pixel fade
- **Rotation Speed**: Chaos Game vertex rotation per rendered frame
- **Feed Rate**: Reaction-Diffusion Gray-Scott feed rate
- **Kill Rate**: Reaction-Diffusion Gray-Scott kill rate
- **Grid Scale**: Reaction-Diffusion simulation downscale factor (2 = 32x32 grid upscaled to 64x64)
- **Seed**: optional deterministic seed; blank means random
- **Reset Engine**: reseed the current engine
- **Pause / Resume**
- **Toggle Grid**
- **Copy Config Snippet**: copy matching `[fallback]` and `[screensaver]` TOML

## Adding Future Screensavers

Keep future engines behind the same small contract:

```python
class Engine:
    def frame(self) -> PIL.Image.Image:
        ...
```

Then register it in `tools/matrix-sim.py` so `/api/meta`, `/api/reset`, and `/api/frame`
can select it.

Good candidates:

- cyclic cellular automata
- sine plasma with lookup tables
- Lissajous / orbit trails

The simulator should stay dependency-light. If a future screensaver needs heavy math,
prototype it here first, then decide whether the daemon should carry that dependency.
