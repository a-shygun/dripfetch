import curses
import time
from pathlib import Path

from ..box import Box
from ..box.base import Border, BoxColors
from ..rain import Rain
from .config import load_config, save_config
from .terminal import Renderer, cleanup, parse_color, setup

# How long to wait, after the last KEY_RESIZE event, before treating a
# terminal resize as "finished" and doing one full clean redraw. While
# events keep arriving faster than this, we hold on the placeholder
# screen instead of trying to render every intermediate size.
RESIZE_SETTLE = 0.5


class App:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config = None
        self.renderer = None
        self.box = None
        self.rain = None
        self.paused = False
        self.resizing = False
        self.last_resize = 0.0
        self.placeholder_colors = None

    def initialize(self, stdscr):
        self.config = load_config(self.config_path)
        setup(stdscr)
        background = parse_color(self.config.get("background", "#000000FF"))
        self.renderer = Renderer(
            stdscr,
            background,
        )
        self.renderer.resize()
        self.box = Box(
            stdscr=stdscr,
            config=self.config,
            config_path=self.config_path,
            renderer=self.renderer,
            save_config=save_config,
        )
        self.rain = Rain(
            stdscr=stdscr,
            config=self.config,
            box=self.box,
            renderer=self.renderer,
        )
        self.placeholder_colors = BoxColors(self.config)

    def handle_mouse(self):
        try:
            _, x, y, _, state = curses.getmouse()
        except curses.error:
            return
        # See terminal.setup(): some terminals never emit BUTTON1_CLICKED,
        # only PRESSED/RELEASED, so treat either as a selection click.
        if state & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
            self.box.handle_mouse(x, y)

    def handle_key(self, key):
        if key == ord("q"):
            return False
        if key == curses.KEY_RESIZE:
            self._begin_resize()
            return True
        if key == curses.KEY_MOUSE:
            self.handle_mouse()
            return True
        if key == ord(" "):
            self.paused = not self.paused
            if self.paused:
                self.rain.pause()
            else:
                self.rain.resume()
            return True
        self.box.handle_key(key)
        return True

    def _begin_resize(self):
        if not self.resizing:
            self.resizing = True
            # Don't stomp on a user-initiated pause (spacebar): only
            # freeze the rain ourselves if it wasn't already paused, and
            # only resume it ourselves in _finish_resize if we're the
            # ones who paused it.
            if not self.paused:
                self.rain.pause()
            self.renderer.invalidate()
        self.last_resize = time.monotonic()

    def _finish_resize(self):
        self.resizing = False
        if not self.paused:
            self.rain.resume()
        self.box.resize()
        self.rain.resize()
        # See Renderer.invalidate(): curses' resizeterm() can flush its
        # own output after ours, silently corrupting whichever cells
        # never get an explicit draw() call. Force one full repaint here
        # so we're not trusting stale assumptions about what the
        # terminal currently shows.
        self.renderer.invalidate()

    def _draw_resize_placeholder(self):
        self.renderer.begin()
        width, height = self.renderer.width, self.renderer.height

        label = "(resizing)"
        dimensions = f"{width} x {height}"
        inner_width = max(len(label), len(dimensions))
        box_width = inner_width + 4
        box_height = 4

        x = max(0, (width - box_width) // 2)
        y = max(0, (height - box_height) // 2)

        Border("single").draw(
            self.renderer,
            x,
            y,
            box_width,
            box_height,
            self.placeholder_colors.border,
        )
        self.renderer.draw(
            x + (box_width - len(label)) // 2,
            y + 1,
            label,
            self.placeholder_colors.text,
        )
        self.renderer.draw(
            x + (box_width - len(dimensions)) // 2,
            y + 2,
            dimensions,
            self.placeholder_colors.text,
        )

        self.renderer.end()

    def update(self):
        if self.resizing:
            if time.monotonic() - self.last_resize < RESIZE_SETTLE:
                self._draw_resize_placeholder()
                return
            self._finish_resize()

        resized = self.renderer.begin()
        if resized:
            self.box.resize()
            self.rain.resize()
        if not self.paused:
            self.rain.update()
        self.box.update()
        self.rain.draw()
        self.box.draw()
        self.renderer.end()

    def run(self, stdscr):
        try:
            self.initialize(stdscr)
            stdscr.nodelay(True)
            stdscr.timeout(10)
            while self.handle_key(stdscr.getch()):
                self.update()
        finally:
            if self.box:
                self.box.close()
            if self.rain:
                self.rain.close()
            cleanup()