import curses
import os
import sys
from contextlib import suppress
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RGBA:
    r: int
    g: int
    b: int
    a: int = 255


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
    """Virtual screen buffer that flushes only the cells changed since the
    previous frame, as raw truecolor ANSI escapes.

    Every call to begin() rebuilds `current` as the target state for this
    frame (background everywhere, then draw() calls paint over it). end()
    then diffs `current` against `previous` (what was actually last written
    to the terminal) and only emits escapes for cells that differ. This
    keeps per-frame output proportional to what's moving on screen (rain
    drops, a blinking clock colon) rather than the full width * height of
    the terminal, which matters a lot at ~100 updates/sec.
    """

    def __init__(self, stdscr, background):
        self.stdscr = stdscr
        self.background = background
        self.width = 0
        self.height = 0
        self.current = {}
        self.previous = {}

    def resize(self):
        height, width = self.stdscr.getmaxyx()
        if (width, height) == (self.width, self.height):
            return False
        self.width = width
        self.height = height
        self.current.clear()
        self.previous.clear()
        with suppress(curses.error):
            curses.resizeterm(height, width)
        return True

    def invalidate(self):
        """Force the next end() call to repaint every cell, ignoring the
        diff. Use this whenever the physical terminal may have fallen out
        of sync with what we last wrote -- e.g. curses' own resize
        handling (curses.resizeterm above) can flush output of its own to
        the terminal *after* our end() write for that frame, silently
        overwriting cells we believe are already correct. Cells that get
        redrawn every frame regardless (rain, a ticking clock) self-heal
        from that; static ones (a box's empty interior) don't, since our
        diff sees current == previous and skips rewriting them -- even
        though the actual terminal no longer matches. Clearing `previous`
        here makes every cell look "changed" for one frame, so the whole
        screen gets repainted from scratch instead of trusting that
        stale assumption.
        """
        self.previous = {}

    def begin(self):
        resized = self.resize()
        background = self.background
        self.current = {
            (x, y): (" ", None, background)
            for y in range(self.height)
            for x in range(self.width)
        }
        return resized

    def draw(self, x, y, text, foreground=None, background=None):
        if not text or y < 0 or y >= self.height:
            return
        background = self.background if background is None else background
        start = max(0, x)
        end = min(x + len(text), self.width)
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

    def _background(self, color):
        if color is None:
            color = self.background
        if not color.a:
            return "\x1b[49m"
        return f"\x1b[48;2;{color.r};{color.g};{color.b}m"

    def end(self):
        previous = self.previous
        current = self.current
        changed = [key for key, cell in current.items() if previous.get(key) != cell]
        if changed:
            output = []
            foreground = background = object()  # sentinels: match no real color
            last_x = last_y = -1
            for x, y in changed:
                character, color, bg = current[(x, y)]
                if y != last_y or x != last_x:
                    output.append(f"\x1b[{y + 1};{x + 1}H")
                if color != foreground:
                    output.append(self._foreground(color))
                    foreground = color
                if bg != background:
                    output.append(self._background(bg))
                    background = bg
                output.append(character)
                last_x = x + 1
                last_y = y
            output.append("\x1b[0m")
            terminal_write("".join(output))
        self.previous = current


def terminal_write(sequence):
    with suppress(OSError):
        os.write(sys.stdout.fileno(), sequence.encode())


def setup(stdscr):
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.use_default_colors()
    # Requesting only BUTTON1_CLICKED is unreliable: a lot of terminals
    # (tmux, SSH sessions, some emulators, or just a fast click) never
    # deliver a "clean" click -- ncurses only synthesizes CLICKED when it
    # sees a press followed by a release inside a short window, and if
    # that window is missed you get PRESSED/RELEASED with no CLICKED at
    # all. Request those too so app.py's handle_mouse has something to
    # react to either way.
    curses.mousemask(
        curses.BUTTON1_CLICKED
        | curses.BUTTON1_PRESSED
        | curses.BUTTON1_RELEASED
    )
    stdscr.keypad(True)
    stdscr.leaveok(True)
    terminal_write("\x1b[?1049h\x1b[2J\x1b[H")


def cleanup():
    terminal_write("\x1b[0m\x1b[?1049l")