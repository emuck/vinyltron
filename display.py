import logging
import sys
from typing import Dict, NamedTuple, Optional, Tuple

from PIL import Image

sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')
from rgbmatrix import RGBMatrix, RGBMatrixOptions

log = logging.getLogger(__name__)


FONT_3X5: Dict[str, Tuple[int, ...]] = {
    ' ': (0b000, 0b000, 0b000, 0b000, 0b000),
    '-': (0b000, 0b000, 0b111, 0b000, 0b000),
    '/': (0b001, 0b001, 0b010, 0b100, 0b100),
    '.': (0b000, 0b000, 0b000, 0b000, 0b010),
    '0': (0b111, 0b101, 0b101, 0b101, 0b111),
    '1': (0b010, 0b110, 0b010, 0b010, 0b111),
    '2': (0b111, 0b001, 0b111, 0b100, 0b111),
    '3': (0b111, 0b001, 0b111, 0b001, 0b111),
    '4': (0b101, 0b101, 0b111, 0b001, 0b001),
    '5': (0b111, 0b100, 0b111, 0b001, 0b111),
    '6': (0b111, 0b100, 0b111, 0b101, 0b111),
    '7': (0b111, 0b001, 0b010, 0b010, 0b010),
    '8': (0b111, 0b101, 0b111, 0b101, 0b111),
    '9': (0b111, 0b101, 0b111, 0b001, 0b111),
    'A': (0b010, 0b101, 0b111, 0b101, 0b101),
    'B': (0b110, 0b101, 0b110, 0b101, 0b110),
    'C': (0b111, 0b100, 0b100, 0b100, 0b111),
    'D': (0b110, 0b101, 0b101, 0b101, 0b110),
    'E': (0b111, 0b100, 0b110, 0b100, 0b111),
    'F': (0b111, 0b100, 0b110, 0b100, 0b100),
    'G': (0b111, 0b100, 0b101, 0b101, 0b111),
    'H': (0b101, 0b101, 0b111, 0b101, 0b101),
    'I': (0b111, 0b010, 0b010, 0b010, 0b111),
    'J': (0b001, 0b001, 0b001, 0b101, 0b111),
    'K': (0b101, 0b101, 0b110, 0b101, 0b101),
    'L': (0b100, 0b100, 0b100, 0b100, 0b111),
    'M': (0b101, 0b111, 0b111, 0b101, 0b101),
    'N': (0b101, 0b111, 0b111, 0b111, 0b101),
    'O': (0b111, 0b101, 0b101, 0b101, 0b111),
    'P': (0b111, 0b101, 0b111, 0b100, 0b100),
    'Q': (0b111, 0b101, 0b101, 0b111, 0b001),
    'R': (0b110, 0b101, 0b110, 0b101, 0b101),
    'S': (0b111, 0b100, 0b111, 0b001, 0b111),
    'T': (0b111, 0b010, 0b010, 0b010, 0b010),
    'U': (0b101, 0b101, 0b101, 0b101, 0b111),
    'V': (0b101, 0b101, 0b101, 0b101, 0b010),
    'W': (0b101, 0b101, 0b111, 0b111, 0b101),
    'X': (0b101, 0b101, 0b010, 0b101, 0b101),
    'Y': (0b101, 0b101, 0b010, 0b010, 0b010),
    'Z': (0b111, 0b001, 0b010, 0b100, 0b111),
}


class TextOverlay(NamedTuple):
    text: str
    color_rgb: Tuple[int, int, int]


class ProgressOverlay(NamedTuple):
    filled_width: int
    height: int
    foreground_rgb: Tuple[int, int, int]
    background_rgb: Optional[Tuple[int, int, int]]


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
        self._current_image = Image.new('RGB', self._size, (0, 0, 0))
        self._text_overlay = None
        self._progress_overlay = None

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
        self._current_image = processed.copy()
        self._render()

    def show_fallback(self):
        self._current_image = self._fallback.copy()
        self._text_overlay = None
        self._progress_overlay = None
        self._render()

    def show_text(self, text: str, color_rgb: Tuple[int, int, int]):
        self._text_overlay = TextOverlay(self._fit_text(text), color_rgb)
        self._render()

    def clear_badge(self):
        self.clear_text()

    def clear_text(self):
        self._text_overlay = None
        self._render()

    def show_progress(
        self,
        filled_width: int,
        height: int,
        foreground_rgb: Tuple[int, int, int],
        background_rgb: Optional[Tuple[int, int, int]],
    ):
        filled_width = max(0, min(self._size[0], int(filled_width)))
        height = max(1, min(self._size[1], int(height)))
        self._progress_overlay = ProgressOverlay(filled_width, height, foreground_rgb, background_rgb)
        self._render()

    def clear_progress(self):
        self._progress_overlay = None
        self._render()

    def _render(self):
        img = self._current_image.copy()

        if self._progress_overlay:
            self._draw_progress(img, self._progress_overlay)

        if self._text_overlay:
            self._draw_text(img, self._text_overlay)

        self._canvas.SetImage(img, unsafe=False)
        self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def _draw_text(self, img: Image.Image, overlay):
        pixels = img.load()
        x0, y0 = 2, 2
        text_width = self._text_width(overlay.text)

        for y in range(y0 - 1, y0 + 6):
            for x in range(x0 - 1, min(self._size[0], x0 + text_width + 1)):
                if 0 <= x < self._size[0] and 0 <= y < self._size[1]:
                    pixels[x, y] = (0, 0, 0)

        cursor = x0
        for char in overlay.text:
            glyph = FONT_3X5.get(char, FONT_3X5[' '])
            for y, row in enumerate(glyph):
                for x in range(3):
                    if row & (1 << (2 - x)):
                        px = cursor + x
                        py = y0 + y
                        if 0 <= px < self._size[0] and 0 <= py < self._size[1]:
                            pixels[px, py] = overlay.color_rgb
            cursor += 4

    def _draw_progress(self, img: Image.Image, overlay):
        pixels = img.load()
        y0 = self._size[1] - overlay.height

        if overlay.background_rgb is not None:
            for y in range(y0, self._size[1]):
                for x in range(self._size[0]):
                    pixels[x, y] = overlay.background_rgb

        for y in range(y0, self._size[1]):
            for x in range(overlay.filled_width):
                pixels[x, y] = overlay.foreground_rgb

    def reconfigure(self, cfg: dict):
        """Hot-reload brightness, gamma, and fallback image. Matrix geometry requires restart."""
        d = cfg['display']
        self._matrix.brightness = d['brightness']
        self._gamma_lut = _build_gamma_lut(d['gamma'])
        self._fallback = self._load_fallback(cfg['fallback']['image'])

    def clear(self):
        self._canvas.Clear()
        self._canvas = self._matrix.SwapOnVSync(self._canvas)
        self._current_image = Image.new('RGB', self._size, (0, 0, 0))
        self._text_overlay = None
        self._progress_overlay = None

    def _fit_text(self, text: str) -> str:
        text = ''.join(ch for ch in text.upper() if ch in FONT_3X5)
        while text and self._text_width(text) > self._size[0] - 4:
            text = text[:-1]
        return text

    def _text_width(self, text: str) -> int:
        if not text:
            return 0
        return len(text) * 4 - 1
