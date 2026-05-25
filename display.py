import logging
import sys
from typing import Optional

from PIL import Image, ImageFilter

sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')
from rgbmatrix import RGBMatrix, RGBMatrixOptions

log = logging.getLogger(__name__)

# Gamma LUT: maps 0-255 linear → gamma-corrected 0-255
def _build_gamma_lut(gamma: float):
    single = bytes(int((i / 255.0) ** gamma * 255 + 0.5) for i in range(256))
    return single * 3  # Pillow needs 768 entries for RGB (256 per channel)


class Display:
    def __init__(self, cfg: dict):
        d = cfg['display']
        opts = RGBMatrixOptions()
        opts.rows = d['rows']
        opts.cols = d['cols']
        opts.brightness = d['brightness']
        opts.gpio_slowdown = d['slowdown_gpio']
        if d.get('pwm_bits'):
            opts.pwm_bits = d['pwm_bits']
        opts.hardware_mapping = 'regular'
        opts.disable_hardware_pulsing = True
        opts.pixel_mapper_config = f"Rotate:{d['rotation']}"
        if d.get('panel_type'):
            opts.panel_type = d['panel_type']

        self._matrix = RGBMatrix(options=opts)
        self._canvas = self._matrix.CreateFrameCanvas()
        self._size = (d['cols'], d['rows'])
        self._gamma_lut = _build_gamma_lut(d['gamma'])
        self._fallback = self._load_fallback(cfg['fallback']['image'])

    def _load_fallback(self, path: str) -> Image.Image:
        try:
            img = Image.open(path).convert('RGB')
            return self._process(img)
        except Exception as e:
            log.warning("Could not load fallback image %s: %s — using blank", path, e)
            return Image.new('RGB', self._size, (0, 0, 0))

    def _process(self, img: Image.Image) -> Image.Image:
        img = img.resize(self._size, Image.LANCZOS)
        img = img.point(self._gamma_lut)
        return img

    def show_image(self, img: Image.Image):
        processed = self._process(img)
        self._canvas.SetImage(processed, unsafe=False)
        self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def show_fallback(self):
        self._canvas.SetImage(self._fallback, unsafe=False)
        self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def reconfigure(self, cfg: dict):
        """Hot-reload brightness, gamma, and fallback image. Matrix geometry requires restart."""
        d = cfg['display']
        self._matrix.brightness = d['brightness']
        self._gamma_lut = _build_gamma_lut(d['gamma'])
        self._fallback = self._load_fallback(cfg['fallback']['image'])

    def clear(self):
        self._canvas.Clear()
        self._canvas = self._matrix.SwapOnVSync(self._canvas)
