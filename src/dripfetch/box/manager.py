import curses

from ..app.terminal import parse_color


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
class BoxColors:
    def __init__(self, config, overrides=None):
        box_config = config.get("boxes", {})
        overrides = overrides or {}
        custom = overrides.get("colors", {})
        self.border = self._resolve(
            overrides,
            box_config,
            "border_color",
            "#FFFFFFFF",
        )
        self.text = self._resolve(
            overrides,
            box_config,
            "text_color",
            "#FFFFFFFF",
        )
        self.accent = self._resolve(
            overrides,
            box_config,
            "accent_color",
            "#FFFFFFFF",
        )
        self.background = parse_color(config.get("background", "#00000000"))
        self.title = self._custom(custom, "title", self.accent)
        self.line = self._custom(custom, "line", self.accent)
        self.body = self._custom(custom, "text", self.text)

    @staticmethod
    def _resolve(overrides, box_config, key, default):
        value = overrides.get(
            key,
            box_config.get(key, default),
        )
        return parse_color(value)

    @staticmethod
    def _custom(custom, key, default):
        if not isinstance(custom, dict):
            return default
        value = custom.get(key)
        if value is None:
            return default
        return parse_color(value)

    @property
    def background_enabled(self):
        return self.background.a > 0


# ---------------------------------------------------------------------------
# Borders
# ---------------------------------------------------------------------------
class Border:
    TYPES = {
        "single": ("─", "│", "┌", "┐", "└", "┘"),
        "double": ("═", "║", "╔", "╗", "╚", "╝"),
        "none": ("", "", "", "", "", ""),
    }

    def __init__(self, name="single"):
        self.name = name if name in self.TYPES else "single"

    @property
    def characters(self):
        return self.TYPES[self.name]

    @property
    def visible(self):
        return self.name != "none"

    def dimensions(self, width, height, horizontal, vertical):
        return (
            width + horizontal * 2 + 2,
            height + vertical * 2 + 2,
        )

    def draw(
        self,
        renderer,
        x,
        y,
        width,
        height,
        color,
        selected=False,
    ):
        if not self.visible:
            return
        (
            top,
            side,
            top_left,
            top_right,
            bottom_left,
            bottom_right,
        ) = self.characters
        if selected:
            top_left = "*"
        renderer.draw(
            x,
            y,
            top_left + top * (width - 2) + top_right,
            color,
        )
        renderer.draw(
            x,
            y + height - 1,
            bottom_left + top * (width - 2) + bottom_right,
            color,
        )
        for row in range(y + 1, y + height - 1):
            renderer.draw(
                x,
                row,
                side,
                color,
            )
            renderer.draw(
                x + width - 1,
                row,
                side,
                color,
            )


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
class Placement:
    LAYOUTS = {
        "qwerty": {
            "up": ord("w"),
            "left": ord("a"),
            "down": ord("s"),
            "right": ord("d"),
        },
        "azerty": {
            "up": ord("z"),
            "left": ord("q"),
            "down": ord("s"),
            "right": ord("d"),
        },
        "qwertz": {
            "up": ord("w"),
            "left": ord("a"),
            "down": ord("s"),
            "right": ord("d"),
        },
    }
    ARROW_KEYS = {
        curses.KEY_UP: (0, -1),
        curses.KEY_LEFT: (-1, 0),
        curses.KEY_DOWN: (0, 1),
        curses.KEY_RIGHT: (1, 0),
    }

    def __init__(self, stdscr, layout="qwerty"):
        self.stdscr = stdscr
        self.layout = self._normalize_layout(layout)

    @staticmethod
    def _normalize_layout(layout):
        if not isinstance(layout, str):
            return "qwerty"
        layout = layout.lower()
        if layout in Placement.LAYOUTS:
            return layout
        return "qwerty"

    def _terminal_size(self):
        height, width = self.stdscr.getmaxyx()
        return width, height

    def _movement(self):
        keys = self.LAYOUTS[self.layout]
        return {
            keys["up"]: (0, -1),
            keys["left"]: (-1, 0),
            keys["down"]: (0, 1),
            keys["right"]: (1, 0),
            **self.ARROW_KEYS,
        }

    def center(self, width, height, offset=None):
        terminal_width, terminal_height = self._terminal_size()
        offset = offset or {}
        return [
            (terminal_width - width) // 2 + offset.get("horizontal", 0),
            (terminal_height - height) // 2 + offset.get("vertical", 0),
        ]

    def clamp(self, position, width, height):
        terminal_width, terminal_height = self._terminal_size()
        position[0] = max(
            0,
            min(
                position[0],
                max(0, terminal_width - width),
            ),
        )
        position[1] = max(
            0,
            min(
                position[1],
                max(0, terminal_height - height),
            ),
        )

    def move(self, position, key):
        movement = self._movement().get(key)
        if movement is None:
            return False
        dx, dy = movement
        position[0] += dx
        position[1] += dy
        return True

    def relative(self, position, width, height):
        terminal_width, terminal_height = self._terminal_size()
        return (
            position[0] - (terminal_width - width) // 2,
            position[1] - (terminal_height - height) // 2,
        )


# ---------------------------------------------------------------------------
# Base box
# ---------------------------------------------------------------------------
class BaseBox:
    ALIGNMENT = "left"

    def __init__(
        self,
        stdscr,
        config,
        box_config,
        colors,
        renderer,
    ):
        self.stdscr = stdscr
        self.config = config
        self.box_config = box_config
        self.colors = colors
        self.renderer = renderer

    @property
    def padding(self):
        padding = self.box_config.get("padding", {})
        return (
            padding.get("horizontal", 2),
            padding.get("vertical", 1),
        )

    def content(self):
        return []

    def update(self):
        pass

    def dimensions(self):
        lines = self.content()
        width = max(
            (self._line_width(line) for line in lines),
            default=0,
        )
        return width, len(lines)

    def draw_content(self, x, y, width, height):
        lines = self.content()
        for row, line in enumerate(lines[:height]):
            segments = self._segments(line)
            line_width = self._line_width(segments)
            if self.ALIGNMENT == "center":
                column = x + max(
                    0,
                    (width - line_width) // 2,
                )
            elif self.ALIGNMENT == "right":
                column = x + max(
                    0,
                    width - line_width,
                )
            else:
                column = x
            for text, color in segments:
                if column >= x + width:
                    break
                available = x + width - column
                text = text[:available]
                if text:
                    self.renderer.draw(
                        column,
                        y + row,
                        text,
                        color,
                    )
                column += len(text)

    def close(self):
        pass

    @staticmethod
    def _segments(line):
        if isinstance(line, str):
            return [(line, None)]
        return line

    @classmethod
    def _line_width(cls, line):
        return sum(len(text) for text, _ in cls._segments(line))



import contextlib

from .types.clock import ClockBox
from .types.logo import LogoBox
from .types.sysinfo import SysInfoBox
from .types.text import TextBox
from .types.weather import WeatherBox


# ---------------------------------------------------------------------------
# Box manager
# ---------------------------------------------------------------------------
class BoxManager:
    TYPES = {
        "text": TextBox,
        "sysinfo": SysInfoBox,
        "clock": ClockBox,
        "logo": LogoBox,
        "weather": WeatherBox,
    }

    def __init__(
        self,
        stdscr,
        config,
        config_path,
        renderer,
        save_config,
    ):
        self.stdscr = stdscr
        self.config = config
        self.config_path = config_path
        self.save_config = save_config
        self.renderer = renderer
        self.box_config = config.get("boxes", {})
        self.box_configs = self.box_config.get("items", [])
        keyboard_config = config.get("keyboard", {})
        keyboard_layout = keyboard_config.get(
            "layout",
            "qwerty",
        )
        self.boxes = []
        self.positions = []
        self.selected = None
        self.placement = Placement(
            stdscr,
            keyboard_layout,
        )
        self._terminal_size = None
        self._initialize()

    def _initialize(self):
        self.boxes = [self._create_box(config) for config in self.box_configs]
        self.positions = [self._center(index) for index in range(len(self.boxes))]
        for index in range(len(self.positions)):
            self._clamp(index)
        self._terminal_size = self.stdscr.getmaxyx()

    def _create_box(self, config):
        box_type = config.get("type", "text")
        box_class = self.TYPES.get(
            box_type,
            TextBox,
        )
        colors = BoxColors(
            self.config,
            config,
        )
        return box_class(
            self.stdscr,
            config,
            self.box_config,
            colors,
            self.renderer,
        )

    def _border(self, index):
        config = self.box_configs[index]
        name = config.get(
            "border",
            self.box_config.get(
                "border",
                "single",
            ),
        )
        return Border(name)

    def _dimensions(self, index):
        box = self.boxes[index]
        content_width, content_height = box.dimensions()
        horizontal, vertical = box.padding
        return self._border(index).dimensions(
            content_width,
            content_height,
            horizontal,
            vertical,
        )

    def _content_geometry(self, index, width, height):
        x, y = self.positions[index]
        horizontal, vertical = self.boxes[index].padding
        content_width = width - 2 - horizontal * 2
        content_height = height - 2 - vertical * 2
        return (
            x + 1 + horizontal,
            y + 1 + vertical,
            content_width,
            content_height,
        )

    def _center(self, index):
        width, height = self._dimensions(index)
        return self.placement.center(
            width,
            height,
            self.box_configs[index].get("position"),
        )

    def _clamp(self, index):
        width, height = self._dimensions(index)
        self.placement.clamp(
            self.positions[index],
            width,
            height,
        )

    def resize(self):
        size = self.stdscr.getmaxyx()
        if size == self._terminal_size:
            return
        self._terminal_size = size
        for index in range(len(self.boxes)):
            self.positions[index] = self._center(index)
            self._clamp(index)

    def _relative_position(self, index):
        width, height = self._dimensions(index)
        return self.placement.relative(
            self.positions[index],
            width,
            height,
        )

    def _save_position(self, index):
        horizontal, vertical = self._relative_position(index)
        position = self.box_configs[index].setdefault(
            "position",
            {},
        )
        position["horizontal"] = horizontal
        position["vertical"] = vertical
        with contextlib.suppress(OSError, ValueError):
            self.save_config(
                self.config,
                self.config_path,
            )

    def get_box_bounds(self, index):
        if not 0 <= index < len(self.boxes):
            return None
        x, y = self.positions[index]
        width, height = self._dimensions(index)
        return (
            x,
            y,
            x + width - 1,
            y + height - 1,
        )

    def get_box_bounds_list(self):
        return [self.get_box_bounds(index) for index in range(len(self.boxes))]

    def handle_mouse(self, x, y):
        for index in range(len(self.boxes)):
            bounds = self.get_box_bounds(index)
            if bounds is None:
                continue
            left, top, right, bottom = bounds
            if left <= x <= right and top <= y <= bottom:
                self.selected = index
                return

    def handle_key(self, key):
        # Escape exits box-moving mode.
        if key == 27:
            self.selected = None
            return
        # No selected box means we are not in moving mode.
        if self.selected is None:
            return
        position = self.positions[self.selected]
        if not self.placement.move(position, key):
            return
        self._clamp(self.selected)
        self._save_position(self.selected)

    def update(self):
        for box in self.boxes:
            box.update()

    def draw(self):
        for index, box in enumerate(self.boxes):
            width, height = self._dimensions(index)
            x, y = self.positions[index]
            self._border(index).draw(
                self.renderer,
                x,
                y,
                width,
                height,
                box.colors.border,
                index == self.selected,
            )
            content = self._content_geometry(
                index,
                width,
                height,
            )
            box.draw_content(*content)

    def close(self):
        for box in self.boxes:
            box.close()
