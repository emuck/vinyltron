import random
from typing import Dict, Tuple

from PIL import Image


RGB = Tuple[int, int, int]

BRIANS_BRAIN_PALETTES: Dict[str, Tuple[RGB, RGB]] = {
    'cyan_amber': ((0, 220, 255), (160, 42, 0)),
    'green_magenta': ((60, 255, 80), (90, 0, 150)),
    'blue_red': ((50, 120, 255), (150, 0, 20)),
    'white_violet': ((245, 245, 255), (70, 0, 120)),
}


class BriansBrain:
    def __init__(
        self,
        width: int,
        height: int,
        palette: str = 'cyan_amber',
        density: float = 0.22,
        seed: str = '',
    ):
        self.width = int(width)
        self.height = int(height)
        self.size = self.width * self.height
        self.state = bytearray(self.size)
        self.next_state = bytearray(self.size)
        self.rgb = bytearray(self.size * 3)
        self.neighbors = self._build_neighbors()
        self.ready_rgb, self.dying_rgb = self._palette(palette)
        self.dead_rgb = (0, 0, 0)
        self.random = random.Random(seed or None)
        self.density = max(0.02, min(0.45, float(density)))
        self._seed()

    def _build_neighbors(self):
        neighbors = []
        for y in range(self.height):
            y_up = (y - 1) % self.height
            y_down = (y + 1) % self.height
            row = y * self.width
            row_up = y_up * self.width
            row_down = y_down * self.width
            for x in range(self.width):
                x_left = (x - 1) % self.width
                x_right = (x + 1) % self.width
                neighbors.append((
                    row_up + x_left,
                    row_up + x,
                    row_up + x_right,
                    row + x_left,
                    row + x_right,
                    row_down + x_left,
                    row_down + x,
                    row_down + x_right,
                ))
        return neighbors

    def _palette(self, name: str) -> Tuple[RGB, RGB]:
        return BRIANS_BRAIN_PALETTES.get(name, BRIANS_BRAIN_PALETTES['cyan_amber'])

    def _seed(self):
        state = self.state
        density = self.density
        rand = self.random.random
        for i in range(self.size):
            state[i] = 1 if rand() < density else 0

    def frame(self) -> Image.Image:
        self._step()
        self._render_rgb()
        return Image.frombytes('RGB', (self.width, self.height), bytes(self.rgb))

    def _step(self):
        state = self.state
        next_state = self.next_state
        neighbors = self.neighbors
        active = 0

        for i in range(self.size):
            cell = state[i]
            if cell == 1:
                next_state[i] = 2
                active += 1
            elif cell == 2:
                next_state[i] = 0
            else:
                ready_neighbors = 0
                for n in neighbors[i]:
                    if state[n] == 1:
                        ready_neighbors += 1
                if ready_neighbors == 2:
                    next_state[i] = 1
                    active += 1
                else:
                    next_state[i] = 0

        self.state, self.next_state = self.next_state, self.state
        if active < 8:
            self._seed()

    def _render_rgb(self):
        state = self.state
        rgb = self.rgb
        ready = self.ready_rgb
        dying = self.dying_rgb
        dead = self.dead_rgb

        j = 0
        for cell in state:
            if cell == 1:
                color = ready
            elif cell == 2:
                color = dying
            else:
                color = dead
            rgb[j] = color[0]
            rgb[j + 1] = color[1]
            rgb[j + 2] = color[2]
            j += 3
