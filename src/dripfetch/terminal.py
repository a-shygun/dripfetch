import curses
import os
import sys


class RGBA:
    __slots__ = ("a", "b", "g", "r")

    def __init__(
        self,
        r,
        g,
        b,
        a=255,
    ):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def __eq__(self, other):
        if not isinstance(other, RGBA):
            return NotImplemented
        return (
            self.r == other.r
            and self.g == other.g
            and self.b == other.b
            and self.a == other.a
        )

    def __hash__(self):
        return hash(
            (
                self.r,
                self.g,
                self.b,
                self.a,
            )
        )


def parse_color(value):
    value = value.lstrip("#")
    if len(value) == 6:
        value += "FF"
    if len(value) != 8:
        raise ValueError(f"Invalid color: #{value}")
    try:
        return RGBA(
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
            int(value[6:8], 16),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid color: #{value}") from exc


class Renderer:
    def __init__(
        self,
        stdscr,
        background,
    ):
        self.stdscr = stdscr
        self.background = background
        self.width = 0
        self.height = 0
        self.current = {}

    def resize(self):
        height, width = self.stdscr.getmaxyx()
        if width == self.width and height == self.height:
            return False
        self.width = width
        self.height = height
        self.current.clear()
        try:
            curses.resizeterm(
                height,
                width,
            )
        except curses.error:
            pass
        return True

    def begin(self):
        resized = self.resize()
        self.current = {
            (x, y): (
                " ",
                None,
                self.background,
            )
            for y in range(self.height)
            for x in range(self.width)
        }
        return resized

    def draw(
        self,
        x,
        y,
        text,
        foreground=None,
        background=None,
    ):
        if not text or y < 0 or y >= self.height:
            return
        background = self.background if background is None else background
        start = max(0, x)
        end = min(
            x + len(text),
            self.width,
        )
        for column in range(start, end):
            self.current[(column, y)] = (
                text[column - x],
                foreground,
                background,
            )

    def _foreground(self, color):
        if color is None:
            return "\x1b[39m"
        return f"\x1b[38;2;{color.r};{color.g};{color.b}m"

    def _background_color(self, color):
        if color is None:
            color = self.background
        if not color.a:
            return "\x1b[49m"
        return f"\x1b[48;2;{color.r};{color.g};{color.b}m"

    def end(self):
        output = ["\x1b[H"]
        foreground = None
        background = None
        last_x = -1
        last_y = -1
        for (x, y), (
            character,
            color,
            bg,
        ) in sorted(
            self.current.items(),
            key=lambda item: item[0][1],
        ):
            if y != last_y or x != last_x:
                output.append(f"\x1b[{y + 1};{x + 1}H")
            if color != foreground:
                output.append(self._foreground(color))
                foreground = color
            if bg != background:
                output.append(self._background_color(bg))
                background = bg
            output.append(character)
            last_x = x + 1
            last_y = y
        output.append("\x1b[0m")
        try:
            os.write(
                sys.stdout.fileno(),
                "".join(output).encode(),
            )
        except OSError:
            pass


def terminal_write(sequence):
    try:
        os.write(
            sys.stdout.fileno(),
            sequence.encode(),
        )
    except OSError:
        pass


def setup(stdscr):
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.use_default_colors()
    curses.mousemask(curses.BUTTON1_CLICKED)
    stdscr.keypad(True)
    stdscr.leaveok(True)
    terminal_write("\x1b[?1049h\x1b[?25l\x1b[0m\x1b[2J\x1b[H")


def cleanup():
    terminal_write("\x1b[0m\x1b[?25h\x1b[?1049l")
