#!/usr/bin/env python3
import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from screensavers import BriansBrain, BRIANS_BRAIN_PALETTES, ChaosGame, GrayScott, LangtonsAnt, Lissajous  # noqa: E402
from weather import MockWeatherRenderer  # noqa: E402


WIDTH = 64
HEIGHT = 64


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vinyltron Matrix Simulator</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #111315;
      --panel: #1b1f23;
      --line: #343a40;
      --text: #e6edf3;
      --muted: #9aa4af;
      --accent: #00d9ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      display: grid;
      grid-template-columns: minmax(360px, 720px) 320px;
      min-height: 100vh;
      gap: 0;
    }
    main {
      display: grid;
      place-items: center;
      padding: 24px;
      min-width: 0;
    }
    aside {
      border-left: 1px solid var(--line);
      background: var(--panel);
      padding: 20px;
      overflow: auto;
    }
    canvas {
      width: min(80vmin, 640px);
      height: min(80vmin, 640px);
      image-rendering: pixelated;
      background: #000;
      box-shadow: 0 0 0 1px #000, 0 12px 36px rgba(0, 0, 0, 0.45);
    }
    h1 {
      margin: 0 0 4px;
      font-size: 18px;
      font-weight: 650;
    }
    .sub {
      color: var(--muted);
      margin: 0 0 20px;
    }
    label {
      display: block;
      margin: 14px 0 6px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
    }
    select, input, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #101316;
      color: var(--text);
      padding: 8px 10px;
      font: inherit;
    }
    input[type="range"] {
      padding: 0;
      accent-color: var(--accent);
    }
    button {
      cursor: pointer;
      margin-top: 10px;
    }
    button.primary {
      background: #0b3b46;
      border-color: #0a6071;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 64px;
      gap: 10px;
      align-items: center;
    }
    .status {
      margin-top: 20px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #11161a;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      white-space: pre-wrap;
    }
    .field[hidden] {
      display: none;
    }
    pre {
      margin: 10px 0 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #0d1114;
      color: var(--text);
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      white-space: pre;
    }
    @media (max-width: 860px) {
      body { grid-template-columns: 1fr; }
      aside { border-left: 0; border-top: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <main>
    <canvas id="matrix" width="64" height="64"></canvas>
  </main>
  <aside>
    <h1>Vinyltron Matrix Simulator</h1>
    <p class="sub">64x64 RGB handoff preview</p>

    <label for="engine">Engine</label>
    <select id="engine"></select>

    <label for="palette">Palette</label>
    <select id="palette"></select>

    <label for="fps">Speed</label>
    <select id="fps">
      <option value="4">Slow</option>
      <option value="6" selected>Medium</option>
      <option value="10">Fast</option>
    </select>

    <label for="resetSeconds">Reset Interval</label>
    <input id="resetSeconds" type="number" min="0" value="300">

    <div id="densityField" class="field">
      <label for="density">Density</label>
      <div class="row">
        <input id="density" type="range" min="2" max="45" value="22">
        <output id="densityOut">0.22</output>
      </div>
    </div>

    <div id="antCountField" class="field" hidden>
      <label for="antCount">Ant Count</label>
      <div class="row">
        <input id="antCount" type="range" min="1" max="8" value="4">
        <output id="antCountOut">4</output>
      </div>
    </div>

    <div id="stepsPerFrameField" class="field" hidden>
      <label for="stepsPerFrame">Steps Per Frame</label>
      <div class="row">
        <input id="stepsPerFrame" type="range" min="8" max="256" step="8" value="96">
        <output id="stepsPerFrameOut">96</output>
      </div>
    </div>

    <div id="pointsPerFrameField" class="field" hidden>
      <label for="pointsPerFrame">Points Per Frame</label>
      <div class="row">
        <input id="pointsPerFrame" type="range" min="32" max="1024" step="32" value="320">
        <output id="pointsPerFrameOut">320</output>
      </div>
    </div>

    <div id="fadeField" class="field" hidden>
      <label for="fade">Fade</label>
      <div class="row">
        <input id="fade" type="range" min="0" max="40" value="12">
        <output id="fadeOut">12</output>
      </div>
    </div>

    <div id="rotationSpeedField" class="field" hidden>
      <label for="rotationSpeed">Rotation Speed</label>
      <div class="row">
        <input id="rotationSpeed" type="range" min="-16" max="16" value="2">
        <output id="rotationSpeedOut">2</output>
      </div>
    </div>

    <div id="feedField" class="field" hidden>
      <label for="feed">Feed Rate</label>
      <div class="row">
        <input id="feed" type="range" min="1" max="100" value="55">
        <output id="feedOut">0.055</output>
      </div>
    </div>

    <div id="killField" class="field" hidden>
      <label for="kill">Kill Rate</label>
      <div class="row">
        <input id="kill" type="range" min="1" max="120" value="62">
        <output id="killOut">0.062</output>
      </div>
    </div>

    <div id="gridScaleField" class="field" hidden>
      <label for="gridScale">Grid Scale</label>
      <div class="row">
        <input id="gridScale" type="range" min="1" max="4" value="2">
        <output id="gridScaleOut">2</output>
      </div>
    </div>

    <div id="freqAField" class="field" hidden>
      <label for="freqA">X Frequency</label>
      <div class="row">
        <input id="freqA" type="range" min="1" max="6" value="3">
        <output id="freqAOut">3</output>
      </div>
    </div>

    <div id="freqBField" class="field" hidden>
      <label for="freqB">Y Frequency</label>
      <div class="row">
        <input id="freqB" type="range" min="1" max="6" value="2">
        <output id="freqBOut">2</output>
      </div>
    </div>

    <div id="driftSpeedField" class="field" hidden>
      <label for="driftSpeed">Drift Speed</label>
      <div class="row">
        <input id="driftSpeed" type="range" min="0" max="10" value="2">
        <output id="driftSpeedOut">2</output>
      </div>
    </div>

    <div id="weatherConditionField" class="field" hidden>
      <label for="weatherCondition">Weather Condition</label>
      <select id="weatherCondition">
        <option value="clear">Clear</option>
        <option value="partly_cloudy" selected>Partly Cloudy</option>
        <option value="cloudy">Cloudy</option>
        <option value="rain">Rain</option>
        <option value="storm">Storm</option>
        <option value="snow">Snow</option>
        <option value="fog">Fog</option>
      </select>
    </div>

    <div id="weatherNightField" class="field" hidden>
      <label for="weatherNight">Weather Time</label>
      <select id="weatherNight">
        <option value="0" selected>Daytime</option>
        <option value="1">Night / Moon</option>
      </select>
    </div>

    <div id="moonPhaseField" class="field" hidden>
      <label for="moonPhase">Moon Phase</label>
      <div class="row">
        <input id="moonPhase" type="range" min="0" max="100" value="55">
        <output id="moonPhaseOut">0.55</output>
      </div>
    </div>

    <div id="secondaryMetricField" class="field" hidden>
      <label for="secondaryMetric">Bottom Metric</label>
      <select id="secondaryMetric">
        <option value="humidity" selected>Humidity</option>
        <option value="aqi">AQI</option>
        <option value="wind">Wind</option>
      </select>
    </div>

    <label for="seed">Seed</label>
    <input id="seed" type="text" value="" placeholder="blank = random">

    <button id="reset" class="primary">Reset Engine</button>
    <button id="pause">Pause</button>
    <button id="grid">Toggle Grid</button>
    <button id="copyToml">Copy Config Snippet</button>

    <label for="toml">Config Snippet</label>
    <pre id="toml"></pre>

    <div id="status" class="status">loading...</div>
  </aside>
  <script>
    const canvas = document.getElementById('matrix');
    const ctx = canvas.getContext('2d', { alpha: false });
    const imageData = ctx.createImageData(64, 64);
    const state = {
      running: true,
      grid: false,
      timer: null,
      frameCount: 0,
      lastStatsAt: performance.now(),
      measuredFps: 0,
    };

    const $ = (id) => document.getElementById(id);
    const engine = $('engine');
    const palette = $('palette');
    const fps = $('fps');
    const resetSeconds = $('resetSeconds');
    const density = $('density');
    const densityOut = $('densityOut');
    const densityField = $('densityField');
    const antCount = $('antCount');
    const antCountOut = $('antCountOut');
    const antCountField = $('antCountField');
    const stepsPerFrame = $('stepsPerFrame');
    const stepsPerFrameOut = $('stepsPerFrameOut');
    const stepsPerFrameField = $('stepsPerFrameField');
    const pointsPerFrame = $('pointsPerFrame');
    const pointsPerFrameOut = $('pointsPerFrameOut');
    const pointsPerFrameField = $('pointsPerFrameField');
    const fade = $('fade');
    const fadeOut = $('fadeOut');
    const fadeField = $('fadeField');
    const rotationSpeed = $('rotationSpeed');
    const rotationSpeedOut = $('rotationSpeedOut');
    const rotationSpeedField = $('rotationSpeedField');
    const feed = $('feed');
    const feedOut = $('feedOut');
    const feedField = $('feedField');
    const kill = $('kill');
    const killOut = $('killOut');
    const killField = $('killField');
    const gridScale = $('gridScale');
    const gridScaleOut = $('gridScaleOut');
    const gridScaleField = $('gridScaleField');
    const freqA = $('freqA');
    const freqAOut = $('freqAOut');
    const freqAField = $('freqAField');
    const freqB = $('freqB');
    const freqBOut = $('freqBOut');
    const freqBField = $('freqBField');
    const driftSpeed = $('driftSpeed');
    const driftSpeedOut = $('driftSpeedOut');
    const driftSpeedField = $('driftSpeedField');
    const weatherCondition = $('weatherCondition');
    const weatherConditionField = $('weatherConditionField');
    const weatherNight = $('weatherNight');
    const weatherNightField = $('weatherNightField');
    const moonPhase = $('moonPhase');
    const moonPhaseOut = $('moonPhaseOut');
    const moonPhaseField = $('moonPhaseField');
    const secondaryMetric = $('secondaryMetric');
    const secondaryMetricField = $('secondaryMetricField');
    const seed = $('seed');
    const toml = $('toml');
    const status = $('status');

    function qs() {
      return new URLSearchParams({
        engine: engine.value,
        palette: palette.value,
        fps: fps.value,
        reset_seconds: resetSeconds.value,
        density: (parseInt(density.value, 10) / 100).toFixed(2),
        ant_count: antCount.value,
        steps_per_frame: stepsPerFrame.value,
        points_per_frame: pointsPerFrame.value,
        fade: fade.value,
        rotation_speed: rotationSpeed.value,
        feed: (parseInt(feed.value, 10) / 1000).toFixed(3),
        kill: (parseInt(kill.value, 10) / 1000).toFixed(3),
        grid_scale: gridScale.value,
        freq_a: freqA.value,
        freq_b: freqB.value,
        drift_speed: driftSpeed.value,
        weather_condition: weatherCondition.value,
        weather_night: weatherNight.value,
        moon_phase: (parseInt(moonPhase.value, 10) / 100).toFixed(2),
        secondary_metric: secondaryMetric.value,
        seed: seed.value,
      });
    }

    async function loadMeta() {
      const res = await fetch('/api/meta');
      const meta = await res.json();
      engine.innerHTML = '';
      for (const item of meta.engines) {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item.label;
        engine.appendChild(opt);
      }
      palette.innerHTML = '';
      for (const item of meta.palettes) {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item.label;
        palette.appendChild(opt);
      }
      updateLabels();
      await resetEngine();
      tick();
    }

    async function resetEngine() {
      await fetch('/api/reset?' + qs().toString(), { method: 'POST' });
    }

    function updateLabels() {
      densityOut.textContent = (parseInt(density.value, 10) / 100).toFixed(2);
      antCountOut.textContent = antCount.value;
      stepsPerFrameOut.textContent = stepsPerFrame.value;
      pointsPerFrameOut.textContent = pointsPerFrame.value;
      fadeOut.textContent = fade.value;
      rotationSpeedOut.textContent = rotationSpeed.value;
      feedOut.textContent = (parseInt(feed.value, 10) / 1000).toFixed(3);
      killOut.textContent = (parseInt(kill.value, 10) / 1000).toFixed(3);
      gridScaleOut.textContent = gridScale.value;
      freqAOut.textContent = freqA.value;
      freqBOut.textContent = freqB.value;
      driftSpeedOut.textContent = driftSpeed.value;
      moonPhaseOut.textContent = (parseInt(moonPhase.value, 10) / 100).toFixed(2);
      resetSeconds.hidden = engine.value === 'weather';
      resetSeconds.previousElementSibling.hidden = engine.value === 'weather';
      seed.hidden = engine.value === 'weather';
      seed.previousElementSibling.hidden = engine.value === 'weather';
      densityField.hidden = engine.value !== 'brians_brain';
      antCountField.hidden = engine.value !== 'langtons_ant';
      stepsPerFrameField.hidden = engine.value !== 'langtons_ant';
      pointsPerFrameField.hidden = engine.value !== 'chaos_game';
      fadeField.hidden = engine.value !== 'chaos_game';
      rotationSpeedField.hidden = engine.value !== 'chaos_game';
      feedField.hidden = engine.value !== 'gray_scott';
      killField.hidden = engine.value !== 'gray_scott';
      gridScaleField.hidden = engine.value !== 'gray_scott';
      freqAField.hidden = engine.value !== 'lissajous';
      freqBField.hidden = engine.value !== 'lissajous';
      driftSpeedField.hidden = engine.value !== 'lissajous';
      fadeField.hidden = engine.value !== 'chaos_game' && engine.value !== 'lissajous';
      weatherConditionField.hidden = engine.value !== 'weather';
      weatherNightField.hidden = engine.value !== 'weather';
      moonPhaseField.hidden = engine.value !== 'weather' || weatherNight.value !== '1';
      secondaryMetricField.hidden = engine.value !== 'weather';
      updateToml();
    }

    function tomlString(value) {
      return '"' + value.split('\\\\').join('\\\\\\\\').split('"').join('\\\\"') + '"';
    }

    function configSnippet() {
      if (engine.value === 'weather') {
        return [
          '[fallback]',
          'mode = "weather"',
          '',
          '[weather]',
          `fps = ${parseInt(fps.value, 10)}`,
          `mock_condition = ${tomlString(weatherCondition.value)}`,
          `mock_night = ${weatherNight.value === '1' ? 'true' : 'false'}`,
          `mock_moon_phase = ${(parseInt(moonPhase.value, 10) / 100).toFixed(2)}`,
          `secondary_metric = ${tomlString(secondaryMetric.value)}`,
        ].join('\\n');
      }
      const lines = [
        '[fallback]',
        'mode = "screensaver"',
        '',
        '[screensaver]',
        `engine = ${tomlString(engine.value)}`,
        `palette = ${tomlString(palette.value)}`,
        `fps = ${parseInt(fps.value, 10)}`,
        `reset_seconds = ${Math.max(0, parseInt(resetSeconds.value || '0', 10) || 0)}`,
      ];
      if (engine.value === 'brians_brain') {
        lines.push(`density = ${(parseInt(density.value, 10) / 100).toFixed(2)}`);
      }
      if (engine.value === 'langtons_ant') {
        lines.push(`ant_count = ${parseInt(antCount.value, 10)}`);
        lines.push(`steps_per_frame = ${parseInt(stepsPerFrame.value, 10)}`);
      }
      if (engine.value === 'chaos_game') {
        lines.push(`points_per_frame = ${parseInt(pointsPerFrame.value, 10)}`);
        lines.push(`fade = ${parseInt(fade.value, 10)}`);
        lines.push(`rotation_speed = ${parseInt(rotationSpeed.value, 10)}`);
      }
      if (engine.value === 'gray_scott') {
        lines.push(`feed = ${(parseInt(feed.value, 10) / 1000).toFixed(3)}`);
        lines.push(`kill = ${(parseInt(kill.value, 10) / 1000).toFixed(3)}`);
        lines.push(`grid_scale = ${parseInt(gridScale.value, 10)}`);
      }
      if (engine.value === 'lissajous') {
        lines.push(`freq_a = ${parseInt(freqA.value, 10)}`);
        lines.push(`freq_b = ${parseInt(freqB.value, 10)}`);
        lines.push(`fade = ${parseInt(fade.value, 10)}`);
        lines.push(`drift_speed = ${parseInt(driftSpeed.value, 10)}`);
      }
      lines.push(`seed = ${tomlString(seed.value)}`);
      return lines.join('\\n');
    }

    function updateToml() {
      toml.textContent = configSnippet();
    }

    async function drawFrame() {
      const res = await fetch('/api/frame?' + qs().toString(), { cache: 'no-store' });
      if (!res.ok) throw new Error(await res.text());
      const rgb = new Uint8Array(await res.arrayBuffer());
      const data = imageData.data;
      for (let src = 0, dst = 0; src < rgb.length; src += 3, dst += 4) {
        data[dst] = rgb[src];
        data[dst + 1] = rgb[src + 1];
        data[dst + 2] = rgb[src + 2];
        data[dst + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
      if (state.grid) drawGrid();
      state.frameCount++;
      const now = performance.now();
      if (now - state.lastStatsAt > 1000) {
        state.measuredFps = state.frameCount * 1000 / (now - state.lastStatsAt);
        state.frameCount = 0;
        state.lastStatsAt = now;
      }
      status.textContent = [
        `engine=${engine.value}`,
        `palette=${palette.value}`,
        `target_fps=${fps.value}`,
        `measured_fps=${state.measuredFps.toFixed(1)}`,
        `reset_seconds=${resetSeconds.value}`,
        `density=${densityOut.textContent}`,
        `ant_count=${antCount.value}`,
        `steps_per_frame=${stepsPerFrame.value}`,
        `points_per_frame=${pointsPerFrame.value}`,
        `fade=${fade.value}`,
        `rotation_speed=${rotationSpeed.value}`,
        `feed=${feedOut.textContent}`,
        `kill=${killOut.textContent}`,
        `grid_scale=${gridScale.value}`,
        `freq_a=${freqA.value}`,
        `freq_b=${freqB.value}`,
        `drift_speed=${driftSpeed.value}`,
        `weather_condition=${weatherCondition.value}`,
        `weather_night=${weatherNight.value}`,
        `moon_phase=${moonPhaseOut.textContent}`,
        `secondary_metric=${secondaryMetric.value}`,
      ].join('\\n');
    }

    function drawGrid() {
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.18)';
      ctx.lineWidth = 0.04;
      for (let i = 1; i < 64; i++) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, 64);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(64, i);
        ctx.stroke();
      }
      ctx.restore();
    }

    function tick() {
      clearTimeout(state.timer);
      if (!state.running) return;
      drawFrame().catch((err) => {
        status.textContent = 'error: ' + err.message;
      }).finally(() => {
        state.timer = setTimeout(tick, 1000 / parseInt(fps.value, 10));
      });
    }

    $('reset').addEventListener('click', async () => {
      await resetEngine();
      if (!state.running) await drawFrame();
    });
    $('pause').addEventListener('click', () => {
      state.running = !state.running;
      $('pause').textContent = state.running ? 'Pause' : 'Resume';
      if (state.running) tick();
    });
    $('grid').addEventListener('click', () => {
      state.grid = !state.grid;
      drawFrame();
    });
    $('copyToml').addEventListener('click', async () => {
      await navigator.clipboard.writeText(configSnippet());
      $('copyToml').textContent = 'Copied';
      setTimeout(() => { $('copyToml').textContent = 'Copy Config Snippet'; }, 1000);
    });
    for (const input of [engine, palette, fps, resetSeconds, density, antCount, stepsPerFrame, pointsPerFrame, fade, rotationSpeed, feed, kill, gridScale, freqA, freqB, driftSpeed, weatherCondition, weatherNight, moonPhase, secondaryMetric, seed]) {
      input.addEventListener('change', async () => {
        updateLabels();
        await resetEngine();
      });
      input.addEventListener('input', updateLabels);
    }

    loadMeta();
  </script>
</body>
</html>
"""


def labelize(value):
    return value.replace('_', ' ').title().replace('Brians', "Brian's")


class EngineRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._engine_id = None
        self._params = None
        self._engine = None

    def frame(self, params):
        with self._lock:
            key = self._key(params)
            if self._engine is None or self._params != key:
                self._engine = self._new_engine(params)
                self._params = key
            img = self._engine.frame()
            return img.tobytes()

    def reset(self, params):
        with self._lock:
            self._engine = self._new_engine(params)
            self._params = self._key(params)

    def _key(self, params):
        return (
            params['engine'],
            params['palette'],
            params['density'],
            params['ant_count'],
            params['steps_per_frame'],
            params['points_per_frame'],
            params['fade'],
            params['rotation_speed'],
            params['feed'],
            params['kill'],
            params['grid_scale'],
            params['freq_a'],
            params['freq_b'],
            params['drift_speed'],
            params['weather_condition'],
            params['weather_night'],
            params['moon_phase'],
            params['secondary_metric'],
            params['seed'],
        )

    def _new_engine(self, params):
        if params['engine'] == 'langtons_ant':
            return LangtonsAnt(
                WIDTH,
                HEIGHT,
                palette=params['palette'],
                ant_count=params['ant_count'],
                steps_per_frame=params['steps_per_frame'],
                seed=params['seed'],
            )
        if params['engine'] == 'brians_brain':
            return BriansBrain(
                WIDTH,
                HEIGHT,
                palette=params['palette'],
                density=params['density'],
                seed=params['seed'],
            )
        if params['engine'] == 'chaos_game':
            return ChaosGame(
                WIDTH,
                HEIGHT,
                palette=params['palette'],
                points_per_frame=params['points_per_frame'],
                fade=params['fade'],
                rotation_speed=params['rotation_speed'],
                seed=params['seed'],
            )
        if params['engine'] == 'gray_scott':
            return GrayScott(
                WIDTH,
                HEIGHT,
                palette=params['palette'],
                feed=params['feed'],
                kill=params['kill'],
                grid_scale=params['grid_scale'],
                seed=params['seed'],
            )
        if params['engine'] == 'lissajous':
            return Lissajous(
                WIDTH,
                HEIGHT,
                palette=params['palette'],
                freq_a=params['freq_a'],
                freq_b=params['freq_b'],
                fade=params['fade'],
                drift_speed=params['drift_speed'],
                seed=params['seed'],
            )
        if params['engine'] == 'weather':
            return MockWeatherRenderer(
                WIDTH,
                HEIGHT,
                condition=params['weather_condition'],
                night=params['weather_night'],
                moon_phase=params['moon_phase'],
                secondary_metric=params['secondary_metric'],
            )
        raise ValueError('unsupported engine')


REGISTRY = EngineRegistry()


def request_params(query):
    values = parse_qs(query)
    engine = values.get('engine', ['brians_brain'])[0]
    palette = values.get('palette', ['cyan_amber'])[0]
    try:
        density = float(values.get('density', ['0.22'])[0])
    except ValueError:
        density = 0.22
    try:
        ant_count = int(values.get('ant_count', ['4'])[0])
    except ValueError:
        ant_count = 4
    try:
        steps_per_frame = int(values.get('steps_per_frame', ['96'])[0])
    except ValueError:
        steps_per_frame = 96
    try:
        points_per_frame = int(values.get('points_per_frame', ['320'])[0])
    except ValueError:
        points_per_frame = 320
    try:
        fade = int(values.get('fade', ['12'])[0])
    except ValueError:
        fade = 12
    try:
        rotation_speed = int(values.get('rotation_speed', ['2'])[0])
    except ValueError:
        rotation_speed = 2
    try:
        feed = float(values.get('feed', ['0.055'])[0])
    except ValueError:
        feed = 0.055
    try:
        kill = float(values.get('kill', ['0.062'])[0])
    except ValueError:
        kill = 0.062
    try:
        grid_scale = int(values.get('grid_scale', ['2'])[0])
    except ValueError:
        grid_scale = 2
    try:
        freq_a = int(values.get('freq_a', ['3'])[0])
    except ValueError:
        freq_a = 3
    try:
        freq_b = int(values.get('freq_b', ['2'])[0])
    except ValueError:
        freq_b = 2
    try:
        drift_speed = int(values.get('drift_speed', ['2'])[0])
    except ValueError:
        drift_speed = 2
    weather_condition = values.get('weather_condition', ['partly_cloudy'])[0]
    weather_night = values.get('weather_night', ['0'])[0] in ('1', 'true', 'yes', 'on')
    try:
        moon_phase = float(values.get('moon_phase', ['0.55'])[0])
    except ValueError:
        moon_phase = 0.55
    secondary_metric = values.get('secondary_metric', ['humidity'])[0]
    seed = values.get('seed', [''])[0]
    return {
        'engine': engine,
        'palette': palette,
        'density': max(0.02, min(0.45, density)),
        'ant_count': max(1, min(8, ant_count)),
        'steps_per_frame': max(1, min(512, steps_per_frame)),
        'points_per_frame': max(8, min(2048, points_per_frame)),
        'fade': max(0, min(64, fade)),
        'rotation_speed': max(-16, min(16, rotation_speed)),
        'feed': max(0.0, min(0.1, feed)),
        'kill': max(0.0, min(0.12, kill)),
        'grid_scale': max(1, min(4, grid_scale)),
        'freq_a': max(1, min(6, freq_a)),
        'freq_b': max(1, min(6, freq_b)),
        'drift_speed': max(0, min(10, drift_speed)),
        'weather_condition': weather_condition,
        'weather_night': weather_night,
        'moon_phase': max(0.0, min(1.0, moon_phase)),
        'secondary_metric': secondary_metric,
        'seed': seed,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self._send_html(HTML)
            return
        if parsed.path == '/api/meta':
            self._send_json({
                'width': WIDTH,
                'height': HEIGHT,
                'engines': [
                    {'id': 'brians_brain', 'label': "Brian's Brain"},
                    {'id': 'langtons_ant', 'label': "Langton's Ant"},
                    {'id': 'chaos_game', 'label': "Chaos Game"},
                    {'id': 'gray_scott', 'label': "Reaction-Diffusion"},
                    {'id': 'lissajous', 'label': "Lissajous"},
                    {'id': 'weather', 'label': "Weather"},
                ],
                'palettes': [
                    {'id': name, 'label': labelize(name)}
                    for name in BRIANS_BRAIN_PALETTES
                ],
            })
            return
        if parsed.path == '/api/frame':
            try:
                frame = REGISTRY.frame(request_params(parsed.query))
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
            except Exception as e:
                self._send_text(400, str(e))
            return
        self._send_text(404, 'not found')

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/reset':
            try:
                REGISTRY.reset(request_params(parsed.query))
                self._send_json({'ok': True})
            except Exception as e:
                self._send_text(400, str(e))
            return
        self._send_text(404, 'not found')

    def log_message(self, fmt, *args):
        return

    def _send_html(self, body):
        data = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, body):
        data = json.dumps(body).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, status, body):
        data = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description='Vinyltron 64x64 matrix simulator')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Vinyltron matrix simulator: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
