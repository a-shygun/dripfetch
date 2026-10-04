import curses


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
