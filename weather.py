import math
import os
from typing import Dict, NamedTuple, Tuple

from PIL import Image, ImageDraw


RGB = Tuple[int, int, int]


class WeatherHour(NamedTuple):
    hour: str
    temperature: int
    precipitation: int
    condition: str


class Glyph(NamedTuple):
    rows: Tuple[int, ...]
    width: int
    height: int
    advance: int


class PixelFont(NamedTuple):
    name: str
    glyphs: Dict[str, Glyph]
    height: int
    trim_right: int = 1


class MockWeather(NamedTuple):
    location: str
    condition: str
    is_day: bool
    temperature: int
    high: int
    low: int
    precipitation: int
    humidity: int
    aqi: int
    aqi_valid: bool
    wind_mph: int
    sunrise_min: int
    sunset_min: int
    sun_event: str
    sun_event_min: int
    hours: Tuple[WeatherHour, ...]


FONT_3X5: Dict[str, Tuple[int, ...]] = {
    ' ': (0b000, 0b000, 0b000, 0b000, 0b000),
    '%': (0b101, 0b001, 0b010, 0b100, 0b101),
    '/': (0b001, 0b001, 0b010, 0b100, 0b100),
    '-': (0b000, 0b000, 0b111, 0b000, 0b000),
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
    'C': (0b111, 0b100, 0b100, 0b100, 0b111),
    'D': (0b110, 0b101, 0b101, 0b101, 0b110),
    'F': (0b111, 0b100, 0b110, 0b100, 0b100),
    'H': (0b101, 0b101, 0b111, 0b101, 0b101),
    'I': (0b111, 0b010, 0b010, 0b010, 0b111),
    'L': (0b100, 0b100, 0b100, 0b100, 0b111),
    'M': (0b101, 0b111, 0b111, 0b101, 0b101),
    'N': (0b101, 0b111, 0b111, 0b111, 0b101),
    'O': (0b111, 0b101, 0b101, 0b101, 0b111),
    'P': (0b110, 0b101, 0b110, 0b100, 0b100),
    'R': (0b110, 0b101, 0b110, 0b101, 0b101),
    'S': (0b111, 0b100, 0b111, 0b001, 0b111),
    'T': (0b111, 0b010, 0b010, 0b010, 0b010),
    'W': (0b101, 0b101, 0b111, 0b111, 0b101),
}


BIG_DIGITS: Dict[str, Tuple[int, ...]] = {
    '0': (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    '1': (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    '2': (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    '3': (0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110),
    '4': (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    '5': (0b11111, 0b10000, 0b10000, 0b11110, 0b00001, 0b00001, 0b11110),
    '6': (0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    '7': (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    '8': (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    '9': (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110),
}


CONDITION_COLORS: Dict[str, Tuple[RGB, RGB]] = {
    'clear': ((255, 190, 30), (255, 82, 20)),
    'partly_cloudy': ((255, 190, 30), (100, 210, 255)),
    'cloudy': ((180, 210, 225), (70, 115, 150)),
    'rain': ((70, 185, 255), (40, 80, 190)),
    'storm': ((180, 70, 255), (255, 220, 60)),
    'snow': ((235, 250, 255), (105, 210, 255)),
    'fog': ((160, 190, 205), (70, 100, 120)),
}


SUN_EVENT_GLYPHS: Dict[str, Tuple[int, ...]] = {
    'rise': (
        0b00100,
        0b01110,
        0b00100,
        0b00000,
        0b01110,
        0b10001,
        0b11111,
        0b00000,
    ),
    'set': (
        0b01110,
        0b10001,
        0b11111,
        0b00000,
        0b00100,
        0b01110,
        0b00100,
        0b00000,
    ),
}


def _load_bdf_font(path: str, name: str) -> PixelFont:
    glyphs = {}
    current = None
    in_bitmap = False
    bitmap = []
    font_ascent = None
    font_descent = None
    cap_height = None

    with open(path, 'r', encoding='ascii', errors='ignore') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()

            if parts[0] == 'FONT_ASCENT' and len(parts) > 1:
                font_ascent = int(parts[1])
            elif parts[0] == 'FONT_DESCENT' and len(parts) > 1:
                font_descent = int(parts[1])
            elif parts[0] == 'CAP_HEIGHT' and len(parts) > 1:
                cap_height = int(parts[1])
            elif parts[0] == 'STARTCHAR':
                current = {
                    'encoding': None,
                    'advance': 0,
                    'bbx': (0, 0, 0, 0),
                }
                bitmap = []
                in_bitmap = False
            elif current is not None and parts[0] == 'ENCODING' and len(parts) > 1:
                current['encoding'] = int(parts[1])
            elif current is not None and parts[0] == 'DWIDTH' and len(parts) > 1:
                current['advance'] = int(parts[1])
            elif current is not None and parts[0] == 'BBX' and len(parts) >= 5:
                current['bbx'] = tuple(int(part) for part in parts[1:5])
            elif current is not None and parts[0] == 'BITMAP':
                in_bitmap = True
            elif current is not None and parts[0] == 'ENDCHAR':
                encoding = current['encoding']
                if encoding is not None and 32 <= encoding <= 126:
                    glyphs[chr(encoding)] = _bdf_glyph(current, bitmap, font_ascent)
                current = None
                in_bitmap = False
            elif current is not None and in_bitmap:
                bitmap.append(line)

    if ' ' not in glyphs:
        glyphs[' '] = Glyph(rows=tuple(), width=0, height=0, advance=3)
    if not glyphs:
        raise ValueError("BDF font contains no ASCII glyphs")

    height_candidates = [glyph.height for glyph in glyphs.values()]
    if cap_height:
        height = max(cap_height, max(height_candidates))
    elif font_ascent is not None and font_descent is not None:
        height = font_ascent + font_descent
    else:
        height = max(height_candidates)
    return PixelFont(name=name, glyphs=glyphs, height=height, trim_right=1)


def _bdf_glyph(current, bitmap, font_ascent) -> Glyph:
    width, height, x_offset, y_offset = current['bbx']
    advance = current['advance'] or width + 1
    if width <= 0 or height <= 0:
        return Glyph(rows=tuple(), width=0, height=0, advance=max(1, advance))

    if font_ascent is None:
        top_padding = 0
        glyph_height = height
    else:
        top_padding = max(0, font_ascent - y_offset - height)
        glyph_height = max(height + top_padding, font_ascent)

    rows = [0] * glyph_height
    for src_y, hex_row in enumerate(bitmap[:height]):
        bits = int(hex_row, 16) if hex_row else 0
        total_bits = len(hex_row) * 4
        dst_y = top_padding + src_y
        row = 0
        for x in range(width):
            if bits & (1 << (total_bits - 1 - x)):
                dst_x = x + max(0, x_offset)
                if 0 <= dst_x < max(width + max(0, x_offset), advance):
                    row |= 1 << dst_x
        if 0 <= dst_y < len(rows):
            rows[dst_y] = row

    return Glyph(
        rows=tuple(rows),
        width=max(width + max(0, x_offset), advance),
        height=glyph_height,
        advance=max(1, advance),
    )


class MockWeatherRenderer:
    def __init__(
        self,
        width: int = 64,
        height: int = 64,
        condition: str = 'partly_cloudy',
        night: bool = False,
        moon_phase: float = 0.55,
        secondary_metric: str = 'humidity',
    ):
        self.width = int(width)
        self.height = int(height)
        self.condition = self._normalize_condition(condition)
        self.night = bool(night)
        self.moon_phase = max(0.0, min(1.0, float(moon_phase)))
        self.secondary_metric = self._normalize_secondary_metric(secondary_metric)
        self.frame_count = 0
        self.font = self._load_small_font()
        self.weather = self._mock_weather(self.condition)

    def frame(self) -> Image.Image:
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        self._draw_background(draw)
        if self.night:
            self._draw_moon(draw, 18, 22, 13, self.moon_phase)
        else:
            self._draw_condition_icon(draw, self.weather.condition, self.weather.is_day)
        self._draw_current(draw)
        self.frame_count += 1
        return img

    def _load_small_font(self) -> PixelFont:
        path = 'assets/fonts/spleen-5x8.bdf'
        if not os.path.exists(path):
            return PixelFont(name='fallback_3x5', glyphs={}, height=5, trim_right=1)
        return _load_bdf_font(path, 'spleen')

    def _normalize_condition(self, condition: str) -> str:
        value = str(condition or '').strip().lower()
        if value in CONDITION_COLORS:
            return value
        if value in ('partly', 'partly-cloudy', 'partly cloudy'):
            return 'partly_cloudy'
        return 'partly_cloudy'

    def _normalize_secondary_metric(self, value: str) -> str:
        value = str(value or '').strip().lower()
        if value in ('humidity', 'aqi', 'wind'):
            return value
        return 'humidity'

    def _mock_weather(self, condition: str) -> MockWeather:
        condition_data = {
            'clear': (74, 82, 58, 0, 6, True),
            'partly_cloudy': (68, 74, 55, 20, 8, True),
            'cloudy': (61, 66, 54, 15, 10, True),
            'rain': (58, 63, 51, 70, 12, True),
            'storm': (72, 80, 66, 85, 19, True),
            'snow': (31, 35, 24, 65, 9, True),
            'fog': (52, 59, 48, 10, 4, True),
        }
        temp, high, low, precip, wind, is_day = condition_data[condition]
        if self.night:
            is_day = False
            temp -= 4
        humidity = {
            'clear': 44,
            'partly_cloudy': 62,
            'cloudy': 70,
            'rain': 86,
            'storm': 78,
            'snow': 81,
            'fog': 92,
        }[condition]
        hours = (
            WeatherHour('NOW', temp, precip, condition),
            WeatherHour('12', temp + 1, min(95, precip + 5), condition),
            WeatherHour('3', temp + 3, max(0, precip - 10), condition),
            WeatherHour('6', temp - 1, max(0, precip - 20), 'cloudy'),
            WeatherHour('9', temp - 4, max(0, precip - 25), 'clear'),
            WeatherHour('12', temp - 6, max(0, precip - 30), 'clear'),
        )
        return MockWeather(
            location='MOCK',
            condition=condition,
            is_day=is_day,
            temperature=temp,
            high=high,
            low=low,
            precipitation=precip,
            humidity=humidity,
            aqi=42,
            aqi_valid=True,
            wind_mph=wind,
            sunrise_min=6 * 60 + 11,
            sunset_min=19 * 60 + 23,
            sun_event='rise' if self.night else 'set',
            sun_event_min=(6 * 60 + 11) if self.night else (19 * 60 + 23),
            hours=hours,
        )

    def _draw_background(self, draw: ImageDraw.ImageDraw):
        primary, secondary = CONDITION_COLORS[self.weather.condition]
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            base = int(12 + 10 * (1.0 - t))
            draw.line((0, y, self.width - 1, y), fill=(
                min(32, base + primary[0] // 28),
                min(34, base + primary[1] // 34),
                min(42, base + primary[2] // 24),
            ))
        for x in range(0, self.width, 2):
            y = int(58 + math.sin((x + self.frame_count) * 0.35) * 1.5)
            draw.point((x, y), fill=(secondary[0] // 3, secondary[1] // 3, secondary[2] // 3))

    def _draw_condition_icon(self, draw: ImageDraw.ImageDraw, condition: str, is_day: bool):
        if condition == 'clear':
            self._draw_sun(draw, 17, 20, 10)
        elif condition == 'partly_cloudy':
            self._draw_sun(draw, 12, 16, 8)
            self._draw_cloud(draw, 3 + self._cloud_drift(0, 1), 22)
        elif condition == 'cloudy':
            self._draw_cloud_bank(draw)
        elif condition == 'rain':
            self._draw_cloud(draw, 3 + self._cloud_drift(1, 1), 16)
            self._draw_rain(draw, 6, 35, 28)
        elif condition == 'storm':
            self._draw_cloud(draw, 3 + self._cloud_drift(2, 1), 16, storm=True)
            self._draw_lightning(draw, 18, 34)
            if self.frame_count % 12 in (0, 1):
                draw.rectangle((0, 0, 63, 63), outline=(70, 70, 90))
        elif condition == 'snow':
            self._draw_cloud(draw, 3 + self._cloud_drift(3, 1), 16)
            self._draw_snow(draw, 6, 35, 30)
        elif condition == 'fog':
            self._draw_cloud(draw, 3 + self._cloud_drift(4, 1), 14, shadow=True)
            self._draw_fog(draw, 2, 34)
        else:
            self._draw_sun(draw, 18, 20, 11)

    def _draw_moon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, phase: float):
        rim = (170, 205, 235)
        lit_color = (232, 246, 255)
        shade_color = (16, 24, 45)
        glow = (35, 55, 85)

        draw.ellipse((cx - radius - 2, cy - radius - 2, cx + radius + 2, cy + radius + 2), fill=glow)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=shade_color, outline=rim)

        b = math.cos(phase * 2.0 * math.pi)
        for py in range(cy - radius, cy + radius + 1):
            dy = (py - cy) / float(radius)
            dy2 = dy * dy
            if dy2 > 1.0:
                continue
            limit = math.sqrt(1.0 - dy2)
            for px in range(cx - radius, cx + radius + 1):
                dx = (px - cx) / float(radius)
                if dx * dx + dy2 > 1.0:
                    continue
                lit = dx >= b * limit if phase <= 0.5 else dx <= -b * limit
                if lit:
                    draw.point((px, py), fill=lit_color)

        for x, y in ((5, 8), (9, 44), (28, 9), (31, 37)):
            if (self.frame_count + x + y) % 18 < 10:
                draw.point((x, y), fill=(170, 210, 255))

    def _draw_sun(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int):
        pulse = 1 if self.frame_count % 16 < 8 else 0
        ray = (255, 120, 25)
        core = (255, 205, 35)
        glow = (165, 70, 20)
        draw.ellipse((cx - radius - 2, cy - radius - 2, cx + radius + 2, cy + radius + 2), fill=glow)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=core)
        for dx, dy in ((0, -15), (11, -11), (15, 0), (11, 11), (0, 15), (-11, 11), (-15, 0), (-11, -11)):
            x0 = cx + int(dx * 0.75)
            y0 = cy + int(dy * 0.75)
            x1 = cx + dx + (1 if dx > 0 else -1 if dx < 0 else 0) * pulse
            y1 = cy + dy + (1 if dy > 0 else -1 if dy < 0 else 0) * pulse
            draw.line((x0, y0, x1, y1), fill=ray)

    def _draw_cloud(self, draw: ImageDraw.ImageDraw, x: int, y: int, shadow: bool = False, storm: bool = False):
        shade = (50, 70, 105) if storm else (48, 85, 110) if shadow else (65, 120, 150)
        body = (180, 215, 230) if not storm else (120, 95, 155)
        bright = (235, 250, 255) if not storm else (185, 145, 230)
        draw.rectangle((x + 3, y + 13, x + 31, y + 22), fill=shade)
        draw.ellipse((x + 1, y + 8, x + 15, y + 22), fill=body)
        draw.ellipse((x + 10, y + 3, x + 26, y + 21), fill=bright)
        draw.ellipse((x + 21, y + 9, x + 35, y + 22), fill=body)
        draw.rectangle((x + 7, y + 14, x + 31, y + 22), fill=body)
        draw.line((x + 7, y + 22, x + 31, y + 22), fill=shade)

    def _draw_cloud_bank(self, draw: ImageDraw.ImageDraw):
        self._draw_compact_cloud(
            draw,
            2 + self._cloud_drift(0, 1),
            18,
            body=(170, 205, 225),
            bright=(230, 245, 255),
            shade=(50, 85, 112),
        )
        self._draw_compact_cloud(
            draw,
            7 + self._cloud_drift(1, 1),
            27,
            body=(125, 170, 200),
            bright=(170, 205, 225),
            shade=(35, 65, 95),
        )

    def _draw_compact_cloud(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        body: RGB,
        bright: RGB,
        shade: RGB,
    ):
        draw.rectangle((x + 3, y + 11, x + 24, y + 18), fill=shade)
        draw.ellipse((x + 0, y + 6, x + 11, y + 18), fill=body)
        draw.ellipse((x + 8, y + 2, x + 21, y + 17), fill=bright)
        draw.ellipse((x + 17, y + 7, x + 29, y + 18), fill=body)
        draw.rectangle((x + 5, y + 12, x + 25, y + 18), fill=body)
        draw.line((x + 5, y + 18, x + 25, y + 18), fill=shade)

    def _cloud_drift(self, phase: int, amplitude: int = 1) -> int:
        cycle = 72
        pos = (self.frame_count + phase * 17) % cycle
        half = cycle // 2
        value = pos if pos < half else cycle - pos
        centered = (value / float(half)) * 2.0 - 1.0
        return int(round(centered * amplitude))

    def _draw_rain(self, draw: ImageDraw.ImageDraw, x: int, y: int, width: int):
        colors = ((55, 190, 255), (20, 105, 230))
        offset = self.frame_count % 6
        for i, px in enumerate(range(x, x + width, 5)):
            py = y + ((offset + i * 2) % 8)
            draw.line((px, py, px - 1, py + 4), fill=colors[i % 2])

    def _draw_snow(self, draw: ImageDraw.ImageDraw, x: int, y: int, width: int):
        for i, px in enumerate(range(x, x + width, 6)):
            py = y + ((self.frame_count // 2 + i * 3) % 10)
            c = (235, 250, 255) if i % 2 else (120, 215, 255)
            draw.point((px, py), fill=c)
            draw.point((px - 1, py), fill=c)
            draw.point((px + 1, py), fill=c)
            draw.point((px, py - 1), fill=c)
            draw.point((px, py + 1), fill=c)

    def _draw_fog(self, draw: ImageDraw.ImageDraw, x: int, y: int):
        for i in range(4):
            yy = y + i * 5
            shift = (self.frame_count // 3 + i * 3) % 8
            draw.line((x + shift, yy, x + 34, yy), fill=(125, 160, 175))
            draw.line((x, yy + 2, x + 25 + shift, yy + 2), fill=(65, 100, 120))

    def _draw_lightning(self, draw: ImageDraw.ImageDraw, x: int, y: int):
        bolt = [(x, y), (x + 7, y), (x + 2, y + 10), (x + 10, y + 10), (x - 1, y + 26), (x + 2, y + 14), (x - 5, y + 14)]
        draw.polygon(bolt, fill=(255, 220, 45))
        draw.line((x + 1, y, x + 7, y), fill=(255, 255, 180))

    def _draw_current(self, draw: ImageDraw.ImageDraw):
        temp = str(self.weather.temperature)
        temp_width = len(temp) * 12 - 2
        x = 58 - temp_width
        self._draw_big_text(draw, temp, x, 10, (245, 250, 255), scale=2)
        draw.ellipse((59, 10, 63, 14), outline=(245, 250, 255))
        self._draw_small_text(draw, 'H%s' % self.weather.high, 42, 31, (255, 140, 45))
        self._draw_small_text(draw, 'L%s' % self.weather.low, 42, 41, (95, 190, 255))
        self._draw_secondary_metric(draw, 2, 55)
        self._draw_sun_event(draw, self.weather.sun_event, 33, 55, (255, 190, 35))
        self._draw_small_text(draw, self._minutes_label(self.weather.sun_event_min), 40, 55, (245, 250, 255))

    def _draw_secondary_metric(self, draw: ImageDraw.ImageDraw, x: int, y: int):
        if self.secondary_metric == 'aqi':
            color = self._aqi_color(self.weather.aqi) if self.weather.aqi_valid else (90, 90, 90)
            text = 'A%s' % self.weather.aqi if self.weather.aqi_valid else 'A--'
        elif self.secondary_metric == 'wind':
            color = (155, 225, 255)
            text = 'W%s' % self.weather.wind_mph
        else:
            color = (80, 205, 255)
            text = '%s%%' % self.weather.humidity
        self._draw_small_text(draw, text, x, y, color)

    def _aqi_color(self, aqi: int) -> RGB:
        if aqi <= 50:
            return (0, 228, 0)
        if aqi <= 100:
            return (255, 230, 0)
        if aqi <= 150:
            return (255, 126, 0)
        if aqi <= 200:
            return (255, 45, 45)
        if aqi <= 300:
            return (170, 70, 190)
        return (126, 0, 35)

    def _minutes_label(self, minutes: int) -> str:
        hour = (minutes // 60) % 24
        minute = minutes % 60
        hour12 = hour % 12 or 12
        return "%d:%02d" % (hour12, minute)

    def _draw_sun_event(self, draw: ImageDraw.ImageDraw, event: str, x: int, y: int, color: RGB):
        rows = SUN_EVENT_GLYPHS.get(event, SUN_EVENT_GLYPHS['set'])
        for yy, row in enumerate(rows):
            for xx in range(5):
                if row & (1 << (4 - xx)):
                    draw.point((x + xx, y + yy), fill=color)

    def _draw_small_text(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: RGB):
        if self.font.glyphs:
            cursor = x
            for char in text.upper():
                glyph = self.font.glyphs.get(char, self.font.glyphs.get(' '))
                if glyph is None:
                    continue
                for yy, row in enumerate(glyph.rows):
                    for xx in range(glyph.width):
                        if row & (1 << xx):
                            px = cursor + xx
                            py = y + yy
                            if 0 <= px < self.width and 0 <= py < self.height:
                                draw.point((px, py), fill=color)
                cursor += glyph.advance
            return

        self._draw_text(draw, text, x, y, color)

    def _draw_text(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: RGB):
        cursor = x
        for char in text.upper():
            rows = FONT_3X5.get(char, FONT_3X5[' '])
            for yy, row in enumerate(rows):
                for xx in range(3):
                    if row & (1 << (2 - xx)):
                        draw.point((cursor + xx, y + yy), fill=color)
            cursor += 4

    def _draw_big_text(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: RGB, scale: int = 2):
        cursor = x
        for char in text:
            rows = BIG_DIGITS.get(char)
            if rows is None:
                cursor += 4 * scale
                continue
            for yy, row in enumerate(rows):
                for xx in range(5):
                    if row & (1 << (4 - xx)):
                        draw.rectangle(
                            (
                                cursor + xx * scale,
                                y + yy * scale,
                                cursor + xx * scale + scale - 1,
                                y + yy * scale + scale - 1,
                            ),
                            fill=color,
                        )
            cursor += 6 * scale
