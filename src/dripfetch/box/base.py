import curses

from ..app.terminal import parse_color


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
class BoxColors:
    def __init__(self, config):
        box_config = config.get("boxes", {})
        self.border = parse_color(box_config.get("border_color", "#FFFFFFFF"))
        self.text = parse_color(box_config.get("text_color", "#FFFFFFFF"))
        self.accent = parse_color(box_config.get("accent_color", "#FFFFFFFF"))
        # Matches the default the Renderer fills the screen with in
        # app.py (config.get("background", "#000000FF")). These two must
        # stay in sync: if a config omits "background" entirely, the
        # canvas is opaque black, so background_enabled below should be
        # True to match, not False.
        self.background = parse_color(config.get("background", "#000000FF"))
        self.title = self.accent
        self.line = self.accent
        self.body = self.text

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
        # Titled variants keep only the top and bottom rules; the title is
        # embedded in the top rule without side walls.
        "titled_single": ("─", "", "┌", "┐", "└", "┘"),
        "titled_double": ("═", "", "╔", "╗", "╚", "╝"),
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
        title=None,
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
        top_line = top_left + top * (width - 2) + top_right
        if title:
            top_line = self._embed_title(top_line, title)
        renderer.draw(
            x,
            y,
            top_line,
            color,
        )
        renderer.draw(
            x,
            y + height - 1,
            bottom_left + top * (width - 2) + bottom_right,
            color,
        )
        # Titled types have no side character, so there is nothing to draw
        # down the left/right edges.
        if not side:
            return
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

    @staticmethod
    def _embed_title(line, title):
        # Splice the title into the middle of an already-built border
        # line, leaving the outermost character (corner glyph) on each
        # side untouched, and never growing/shrinking the line. The
        # title gets a 1-character pad on each side.
        width = len(line)
        if width <= 2:
            return line
        title = f" {title} "
        title = title[: width - 2]
        if not title.strip():
            return line
        start = 1 + max(0, (width - 2 - len(title)) // 2)
        end = start + len(title)
        if end > width - 1:
            end = width - 1
            start = end - len(title)
        return line[:start] + title + line[end:]


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
