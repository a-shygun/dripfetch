from pathlib import Path

from .borders import Border
from .colors import BoxColors
from .placement import Placement
from .types.clock import ClockBox
from .types.logo import LogoBox
from .types.sysinfo import SysInfoBox
from .types.text import TextBox
from .types.weather import WeatherBox

class Box:
    TYPES = {
        "text": TextBox,
        "sysinfo": SysInfoBox,
        "clock": ClockBox,
        "logo": LogoBox,
        "weather": WeatherBox,
    }

    def __init__(self, stdscr, config, config_path, renderer, save_config):
        self.stdscr = stdscr
        self.config = config
        self.config_path = Path(config_path)
        self.renderer = renderer
        self.save_config = save_config
        self.boxes = config.get("boxes", {})
        self.items = self.boxes.get("items", [])
        self.renderers = []
        self.positions = []
        self.selected = None
        self.placement = Placement(stdscr)
        self._terminal_size = None
        self._initialize()

    @property
    def padding(self):
        padding = self.boxes.get("padding", {})
        return padding.get("horizontal", 2), padding.get("vertical", 1)

    def _initialize(self):
        self.renderers = [self._create_box(index) for index in range(len(self.items))]
        self.positions = [self._center(index) for index in range(len(self.items))]

        for index in range(len(self.positions)):
            self._clamp(index)

        self._terminal_size = self.stdscr.getmaxyx()

    def _create_box(self, index):
        config = self.items[index]
        cls = self.TYPES.get(config.get("type", "text"), TextBox)
        colors = BoxColors(self.config, config)
        return cls(self.stdscr, config, self.boxes, colors, self.renderer)

    def _border(self, index):
        return Border(
            self.items[index].get("border", self.boxes.get("border", "single"))
        )

    def _dimensions(self, index):
        width, height = self.renderers[index].dimensions()
        horizontal, vertical = self.padding
        return self._border(index).dimensions(
            width + horizontal * 2,
            height + vertical * 2,
            0,
            0,
        )

    def _content_geometry(self, index):
        x, y = self.positions[index]
        horizontal, vertical = self.padding
        width, height = self.renderers[index].dimensions()
        border = self._border(index)
        return x + border.side_width + horizontal, y + 1 + vertical, width, height

    def _center(self, index):
        width, height = self._dimensions(index)
        return self.placement.center(width, height, self.items[index].get("position"))

    def _clamp(self, index):
        width, height = self._dimensions(index)
        self.positions[index] = self.placement.clamp(
            self.positions[index], width, height
        )

    def resize(self):
        size = self.stdscr.getmaxyx()

        if size == self._terminal_size:
            return

        self._terminal_size = size

        for index in range(len(self.items)):
            self.positions[index] = self._center(index)
            self._clamp(index)

    def _relative_position(self, index):
        width, height = self._dimensions(index)
        return self.placement.relative(self.positions[index], width, height)

    def _save_position(self, index):
        horizontal, vertical = self._relative_position(index)
        position = self.items[index].setdefault("position", {})
        position["horizontal"] = horizontal
        position["vertical"] = vertical

        try:
            self.save_config(self.config, self.config_path)
        except (OSError, ValueError):
            pass

    def get_box_bounds(self, index):
        if index >= len(self.items):
            return None

        x, y = self.positions[index]
        width, height = self._dimensions(index)
        return x, y, x + width - 1, y + height - 1

    def get_box_bounds_list(self):
        return [self.get_box_bounds(index) for index in range(len(self.items))]

    def handle_mouse(self, x, y):
        for index in range(len(self.items)):
            bounds = self.get_box_bounds(index)

            if bounds is None:
                continue

            box_x, box_y, right, bottom = bounds

            if box_x <= x <= right and box_y <= y <= bottom:
                self.selected = index
                return

    def handle_key(self, key):
        if key == 27:
            self.selected = None
            return

        if self.selected is None:
            return

        if not self.placement.move(self.positions[self.selected], key):
            return

        self._clamp(self.selected)
        self._save_position(self.selected)

    def draw(self):
        for index in range(len(self.items)):
            self._draw_box(index)

    def _draw_box(self, index):
        x, y = self.positions[index]
        width, height = self._dimensions(index)
        renderer = self.renderers[index]
        colors = renderer.colors

        self._border(index).draw(
            self.renderer,
            x,
            y,
            width,
            height,
            colors.border,
            index == self.selected,
        )

        renderer.draw_content(*self._content_geometry(index))

    def update(self):
        for renderer in self.renderers:
            renderer.update()

    def close(self):
        for renderer in self.renderers:
            renderer.close()