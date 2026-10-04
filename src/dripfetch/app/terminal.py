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

    Every call to begin() starts a fresh `current` dict; draw() calls paint
    into it. Only cells that were actually drawn to end up in `current` --
    unlike the previous implementation, begin() does *not* pre-populate an
    entry for every (x, y) on the screen first. At ~100 updates/sec that
    prefill-the-whole-screen-then-diff-the-whole-screen approach cost two
    full width*height passes every single frame, even when nothing was
    moving (e.g. rain at intensity 0 with a handful of static boxes).
    `previous` is kept sparse too: it only ever holds cells that differ
    from blank background, so its size -- and therefore the cost of
    begin()/draw()/end() -- stays proportional to how much is actually on
    screen (rain drops, box glyphs) instead of the full terminal size.
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
        # Cells that never get an explicit draw() call -- the empty
        # space around/between boxes -- are never represented in
        # `current`/`previous` at all now (see class docstring), so
        # nothing in the normal per-cell diff ever paints them. Without
        # this, those cells simply show whatever the terminal emulator's
        # own default background is instead of the app's configured
        # background. Paint the whole physical screen to the configured
        # background once here, in a single escape sequence, so empty
        # space is correct from the start; the sparse diff only has to
        # account for cells that differ from *that* afterwards.
        self._paint_background()
        return True

    def _paint_background(self):
        terminal_write(f"{self._background(self.background)}\x1b[2J")

    def invalidate(self):
        """Force the next end() call to repaint every drawn cell and make
        sure nothing stale is left over from outside our own tracked
        cells -- e.g. curses' own resize handling (curses.resizeterm
        above) can flush output of its own to the terminal *after* our
        end() write for that frame, silently leaving cells we believe
        are blank actually showing old content.

        Previously this was done by clearing `previous` and relying on
        begin() re-filling `current` with a background entry for every
        cell on the next frame, forcing a full width*height repaint
        through Python. Since `current`/`previous` are sparse now (see
        the class docstring), that trick no longer reaches blank cells.
        Repainting the physical background directly is simpler, cheaper,
        and gives the same guarantee: after this, every untouched cell
        genuinely shows the configured background, so the sparse diff in
        end() stays correct.
        """
        self._paint_background()
        self.previous = {}

    def begin(self):
        resized = self.resize()
        self.current = {}
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
        blank = (" ", None, self.background)

        # Cells drawn this frame that weren't already showing exactly
        # this -- `previous.get(key, blank)` treats "not in previous" as
        # blank, since previous only tracks non-blank cells.
        changed = {
            key: cell
            for key, cell in current.items()
            if previous.get(key, blank) != cell
        }

        # Cells that had content last frame but weren't redrawn this
        # frame (e.g. a raindrop that moved on) need to be cleared.
        for key in previous:
            if key not in current:
                changed[key] = blank

        if changed:
            output = []
            foreground = background = object()  # sentinels: match no real color
            last_x = last_y = -1
            # Sorted so consecutive same-row writes can skip the cursor
            # move most of the time, same as the old row-major ordering
            # that fell out of the previous full-grid prefill for free.
            for (x, y), (character, color, bg) in sorted(
                changed.items(), key=lambda item: (item[0][1], item[0][0])
            ):
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

        # Only remember non-blank cells -- see the class docstring.
        self.previous = {key: cell for key, cell in current.items() if cell != blank}


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