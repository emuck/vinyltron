# Current Weather

Vinyltron can show a weather display as an idle mode. The current implementation is an
MVP scaffold: it uses mock weather data, but the mode routing, plugin settings, renderer,
simulator support, and hardware display path are in place.

Album art still wins. When Volumio artwork is enabled and available, weather stops just
like the other idle modes.

## Enable

Open Vinyltron Settings and set:

- **Idle Mode**: `Current Weather`

The weather-specific controls live in the **Weather** settings section.

For direct TOML testing:

```toml
[fallback]
mode = "weather"

[weather]
fps = 1
mock_condition = "partly_cloudy"
mock_night = false
mock_moon_phase = 0.55
secondary_metric = "humidity"
```

## Weather Settings

These controls are currently renderer-test controls. Live Open-Meteo data will replace the
mock fields in the data-integration pass.

- **Mock Condition**: `Clear`, `Partly Cloudy`, `Cloudy`, `Rain`, `Storm`, `Snow`, `Fog`
- **Mock Night / Moon**: shows moon phase in the large icon area instead of the weather icon
- **Mock Moon Phase**: `0.0` new moon, `0.5` full moon, `1.0` new moon
- **Bottom Metric**: `Humidity`, `AQI`, or `Wind`
- **Animation Speed**: weather renderer frame rate

## Layout

The current 64x64 weather template is optimized for readability:

- large custom temperature digits on the right
- large icon area on the left
- high and low temperatures under the current temperature
- Spleen 5x8 text for small values
- bottom-left secondary metric
- bottom-right next sun-event time, shown with a compact sunrise/sunset glyph

During the day, the large icon area shows the current condition. At night, the same area
can show a computed moon phase. The moon phase renderer is local and does not need an API.

The bottom forecast trend strip from the first mock was removed. Forecast should become a
separate weather screen later rather than competing with current conditions on the Today
screen.

## Icon Animation

Weather icons are drawn directly with Pillow primitives and small pixel glyphs. Cloud-based
conditions use a lightweight drift animation:

- each cloud layer has a small phase offset
- clouds move only about 1 pixel over a slow triangular-wave cycle
- no per-pixel simulation, no allocations, and no heavy math per cloud

This keeps the display alive without distracting from the weather numbers.

## Simulator

Use the matrix simulator to test weather icons and moon phases before deploying:

```bash
python3 tools/matrix-sim.py
```

Open:

```text
http://127.0.0.1:8765
```

Set **Engine** to `Weather`, then use:

- **Weather Condition**
- **Weather Time**
- **Moon Phase**
- **Bottom Metric**
- **Reset Engine**

The simulator imports `weather.py` once at startup. Restart the simulator after editing
the renderer.

## Planned Data Integration

The intended live data source is Open-Meteo:

- forecast API for current temperature, humidity, wind, weather code, daily high/low,
  sunrise, sunset, and timezone-aware local timestamps
- optional air-quality API for US AQI only when AQI is selected
- geocoding API for city lookup after manual latitude/longitude works

Expected future `[weather]` fields:

```toml
[weather]
screen = "today"             # today | forecast | future screens
latitude = 37.7749
longitude = -122.4194
location_label = "San Francisco"
units = "imperial"           # imperial | metric
secondary_metric = "humidity" # humidity | aqi | wind
night_icon = "moon"          # moon | weather
refresh_minutes = 10
```

Future weather screens can be added beside `today`, for example forecast, tides, or night
sky. They should stay under Weather settings rather than becoming screensaver engines.
