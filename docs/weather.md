# Current Weather

Vinyltron can show a weather display as an idle mode. The current implementation is an
MVP current-conditions display. It can use mock weather data for icon testing or live
Open-Meteo data for temperature, condition, high/low, humidity, wind, sunrise, and sunset.
The mode routing, plugin settings, renderer, simulator support, and hardware display path
are in place.

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
source = "mock"                  # mock | open_meteo
latitude = 0.0
longitude = 0.0
location_label = ""
units = "imperial"               # imperial | metric
refresh_minutes = 10
night_icon = "moon"              # moon | weather
secondary_metric = "humidity"    # humidity | aqi | wind
fps = 1
mock_condition = "partly_cloudy"
mock_night = false
mock_moon_phase = 0.55
```

## Weather Settings

The Volumio Weather settings section is user-facing and focused on live current weather:

- **Location Label**: optional friendly name for logs and future screens
- **Latitude / Longitude**: manual coordinates used by Open-Meteo
- **Units**: `Imperial` or `Metric`
- **Refresh**: live data refresh cadence, clamped to 5-60 minutes
- **Night Icon**: show computed moon phase after sunset, or keep the weather icon
- **Bottom Metric**: `Humidity`, `AQI`, or `Wind`
- **Animation Speed**: weather renderer frame rate

Saving the Volumio Weather settings selects the live Open-Meteo source. Mock weather
controls are intentionally kept out of the Volumio panel; use the simulator or direct TOML
editing for icon development.

## Live Data

When `source = "open_meteo"`, Vinyltron fetches the Open-Meteo forecast API in a
background thread and keeps showing the last good frame if a refresh fails. The first frame
falls back to mock data until the first successful fetch completes.

Live current-conditions fields currently used:

- temperature, weather code, day/night flag, humidity, wind speed
- daily high and low
- sunrise and sunset local times from Open-Meteo's timezone-aware response
- optional US AQI from Open-Meteo Air Quality when `secondary_metric = "aqi"`

City lookup is not implemented yet; enter latitude and longitude manually for now.

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

For direct TOML renderer testing, set `source = "mock"` and use:

- **Mock Condition**: `clear`, `partly_cloudy`, `cloudy`, `rain`, `storm`, `snow`, `fog`
- **Mock Night / Moon**: `mock_night = true` shows moon phase in the large icon area
- **Mock Moon Phase**: `0.0` new moon, `0.5` full moon, `1.0` new moon

## Planned Weather Expansion

Future weather screens can be added beside `today`, for example forecast, tides, or night
sky. They should stay under Weather settings rather than becoming screensaver engines.

Likely next steps:

- geocoding API for city lookup after manual latitude/longitude proves stable
- a dedicated forecast screen instead of squeezing forecast into the current screen
- richer night displays, such as visible planets or moonrise/moonset
