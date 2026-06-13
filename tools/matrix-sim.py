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

from screensavers import BriansBrain, BRIANS_BRAIN_PALETTES  # noqa: E402


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

    <label for="fps">FPS</label>
    <div class="row">
      <input id="fps" type="range" min="1" max="30" value="12">
      <output id="fpsOut">12</output>
    </div>

    <label for="density">Density</label>
    <div class="row">
      <input id="density" type="range" min="2" max="45" value="22">
      <output id="densityOut">0.22</output>
    </div>

    <button id="reset" class="primary">Reset Engine</button>
    <button id="pause">Pause</button>
    <button id="grid">Toggle Grid</button>

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
    const fpsOut = $('fpsOut');
    const density = $('density');
    const densityOut = $('densityOut');
    const status = $('status');

    function qs() {
      return new URLSearchParams({
        engine: engine.value,
        palette: palette.value,
        fps: fps.value,
        density: (parseInt(density.value, 10) / 100).toFixed(2),
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
      fpsOut.textContent = fps.value;
      densityOut.textContent = (parseInt(density.value, 10) / 100).toFixed(2);
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
        `density=${densityOut.textContent}`,
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
    for (const input of [engine, palette, fps, density]) {
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
        )

    def _new_engine(self, params):
        if params['engine'] != 'brians_brain':
            raise ValueError('unsupported engine')
        return BriansBrain(
            WIDTH,
            HEIGHT,
            palette=params['palette'],
            density=params['density'],
        )


REGISTRY = EngineRegistry()


def request_params(query):
    values = parse_qs(query)
    engine = values.get('engine', ['brians_brain'])[0]
    palette = values.get('palette', ['cyan_amber'])[0]
    try:
        density = float(values.get('density', ['0.22'])[0])
    except ValueError:
        density = 0.22
    return {
        'engine': engine,
        'palette': palette,
        'density': max(0.02, min(0.45, density)),
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
