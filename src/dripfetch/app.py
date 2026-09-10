import curses
from pathlib import Path

from .box import Box
from .config import (
    DEFAULT_BACKGROUND,
    load_config,
    save_config,
)
from .rain import Rain
from .terminal import (
    Renderer,
    cleanup,
    parse_color,
    setup,
)


class App:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config = None
        self.renderer = None
        self.box = None
        self.rain = None
        self.paused = False

    def initialize(self, stdscr):
        self.config = load_config(self.config_path)
        setup(stdscr)
        background = parse_color(
            self.config.get(
                "background",
                DEFAULT_BACKGROUND,
            )
        )
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

    def handle_mouse(self):
        try:
            _, x, y, _, state = curses.getmouse()
        except curses.error:
            return
        if state & curses.BUTTON1_CLICKED:
            self.box.handle_mouse(
                x,
                y,
            )

    def handle_key(self, key):
        if key == ord("q"):
            return False
        if key == curses.KEY_MOUSE:
            self.handle_mouse()
        elif key == ord(" "):
            self.paused = not self.paused
            if self.paused:
                self.rain.pause()
            else:
                self.rain.resume()
        elif key == 27 or key in (
            ord("w"),
            ord("a"),
            ord("s"),
            ord("d"),
        ):
            self.box.handle_key(key)
        return True

    def update(self):
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
