import time

from .collision import collision, inside_box
from .colors import ColorManager
from .movement import move_down, move_horizontal
from .spawning import spawn


class Rain:
    def __init__(self, stdscr, config, box, renderer):
        self.stdscr = stdscr
        self.config = config
        self.box = box
        self.renderer = renderer
        self.height, self.width = stdscr.getmaxyx()
        self.drops = []
        self.colors = ColorManager()
        self.paused_at = None
        self.spawned = 0
        self.spawned_at = time.monotonic()
        rain = config.get("rain", {})
        self.collision = rain.get("collision", True)
        self.intensity = max(0, float(rain.get("intensity", 1)))
        self.character = rain.get("character", "│")
        self.speeds = rain.get("speeds", [])
        self.lengths = rain.get("lengths", [])
        self.rain_colors = rain.get("colors", [])
        colors = dict.fromkeys(color for _, color in self.rain_colors)
        self.colors.create_pairs(colors or ["#FFFFFF"])

    def _spawn(self, now):
        self.spawned, self.spawned_at = spawn(
            self.drops,
            self.width,
            self.intensity,
            self.spawned,
            self.spawned_at,
            now,
            self.speeds,
            self.lengths,
            self.rain_colors,
        )

    def _collision(self, x, old_y, new_y, bounds):
        return collision(
            x,
            old_y,
            new_y,
            bounds,
            self.collision,
            self.width,
        )

    @staticmethod
    def _inside_box(x, y, bounds):
        return inside_box(x, y, bounds)

    @staticmethod
    def _inside_box(x, y, bounds):
        return inside_box(x, y, bounds)

    def _move_horizontal(self, drop):
        move_horizontal(drop)

    def _move_down(self, drop, bounds):
        move_down(
            drop,
            bounds,
            self.collision,
            self.width,
            self.character,
        )

    def _update_drop(self, drop, now, bounds):
        if not drop.active:
            return
        interval = max(1.0, float(drop.speed)) / 1000
        elapsed = now - drop.last_move
        if elapsed < interval:
            return
        steps = min(
            max(1, int(elapsed / interval)),
            8,
        )
        for _ in range(steps):
            if drop.redirect_target is None:
                self._move_down(drop, bounds)
            else:
                self._move_horizontal(drop)
            if drop.head_y - drop.length >= self.height:
                drop.active = False
                break
        drop.last_move = now

    def _draw_drop(self, drop, bounds):
        if not drop.active:
            return
        for tail, (x, y, character) in enumerate(reversed(drop.path)):
            if tail >= drop.length:
                break
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            if not self.collision and self._inside_box(
                x,
                y,
                bounds,
            ):
                continue
            self.renderer.draw(
                x,
                y,
                character,
                self.colors.attribute(
                    drop.color,
                    tail,
                    drop.length,
                ),
            )

    def update(self):
        now = time.monotonic()
        bounds = self.box.get_box_bounds_list()
        self._spawn(now)
        alive = []
        for drop in self.drops:
            self._update_drop(
                drop,
                now,
                bounds,
            )
            if drop.active:
                alive.append(drop)
        self.drops = alive

    def draw(self):
        bounds = self.box.get_box_bounds_list()
        for drop in self.drops:
            self._draw_drop(
                drop,
                bounds,
            )

    def pause(self):
        if self.paused_at is None:
            self.paused_at = time.monotonic()

    def resume(self):
        if self.paused_at is None:
            return
        delay = time.monotonic() - self.paused_at
        for drop in self.drops:
            drop.last_move += delay
        self.spawned_at += delay
        self.paused_at = None

    def reset_timing(self):
        now = time.monotonic()
        for drop in self.drops:
            drop.last_move = now
        self.spawned_at = now
        self.spawned = 0

    def resize(self):
        height, width = self.stdscr.getmaxyx()
        if (height, width) == (self.height, self.width):
            return False
        self.height = height
        self.width = width
        if self.width <= 0 or self.height <= 0:
            self.drops.clear()
            self.reset_timing()
            return True
        alive = []
        for drop in self.drops:
            if drop.x < 0 or drop.x >= self.width:
                drop.active = False
                continue
            if drop.head_y - drop.length >= self.height:
                drop.active = False
                continue
            if drop.redirect_target is not None:
                if not 0 <= drop.redirect_target < self.width:
                    drop.redirect_target = None
            alive.append(drop)
        self.drops = alive
        self.reset_timing()
        return True

    def close(self):
        self.drops.clear()
