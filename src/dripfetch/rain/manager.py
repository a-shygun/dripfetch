import time

from ..app.terminal import parse_color
from .colors import ColorManager
from .constants import SPLASH_DURATION
from .physics import update_drop
from .rendering import draw_drop, draw_splashes
from .spawning import Spawner


class Rain:
    def __init__(
        self,
        stdscr,
        config,
        box,
        renderer,
    ):
        self.stdscr = stdscr
        self.config = config
        self.box = box
        self.renderer = renderer

        self.height, self.width = (
            stdscr.getmaxyx()
        )

        self.drops = []
        self.splashes = []
        self.colors = ColorManager()

        self.paused_at = None

        # Drop (and splash) tails fade toward this color instead of
        # black. Matches the same background the Renderer fills the
        # screen with and BoxColors falls back to, so rain blends into
        # whatever canvas color the rest of the app is using.
        self.background = parse_color(
            config.get("background", "#000000FF")
        )

        rain_config = config.get("rain", {})

        self.collision = rain_config.get(
            "collision",
            True,
        )

        # Spawning (weighted character/speed/length/color choice and
        # spawn-rate timing) lives in its own object -- see spawning.py.
        self.spawner = Spawner(rain_config)

        # Effects are opt-in and default to off, so nothing changes
        # unless one is explicitly flipped on in config.
        effects = rain_config.get("effects", {})

        self.fx_acceleration = bool(
            effects.get("acceleration", False)
        )
        self.fx_splash = bool(
            effects.get("splash", False)
        )

        colors = dict.fromkeys(
            color
            for _, color in self.spawner.rain_colors
        )

        self.colors.create_pairs(
            colors or ["#FFFFFF"]
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self):
        now = time.monotonic()
        bounds = (
            self.box.get_box_bounds_list()
        )

        self.drops.extend(
            self.spawner.spawn(now, self.width)
        )

        alive = []

        for drop in self.drops:
            update_drop(
                drop,
                now,
                bounds,
                self.width,
                self.height,
                self.collision,
                self.fx_acceleration,
            )

            if drop.active:
                alive.append(drop)

        self.drops = alive

        if self.splashes:
            self.splashes = [
                splash
                for splash in self.splashes
                if now - splash.born < SPLASH_DURATION
            ]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self):
        bounds = (
            self.box.get_box_bounds_list()
        )

        for drop in self.drops:
            draw_drop(
                self.renderer,
                drop,
                bounds,
                self.width,
                self.height,
                self.collision,
                self.colors,
                self.background,
            )

        if self.fx_splash:
            draw_splashes(
                self.renderer,
                self.splashes,
                self.width,
                self.height,
                self.background,
            )

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------
    def pause(self):
        if self.paused_at is None:
            self.paused_at = time.monotonic()

    def resume(self):
        if self.paused_at is None:
            return

        delay = (
            time.monotonic()
            - self.paused_at
        )

        for drop in self.drops:
            drop.last_move += delay
            drop.spawned_at += delay

        for splash in self.splashes:
            splash.born += delay

        self.spawner.spawned_at += delay
        self.paused_at = None

    def reset_timing(self):
        now = time.monotonic()

        for drop in self.drops:
            drop.last_move = now
            drop.spawned_at = now

        self.spawner.reset_timing(now)

    # ------------------------------------------------------------------
    # Resize / cleanup
    # ------------------------------------------------------------------
    def resize(self):
        height, width = (
            self.stdscr.getmaxyx()
        )

        if (
            height,
            width,
        ) == (
            self.height,
            self.width,
        ):
            return False

        self.height = height
        self.width = width

        if (
            self.width <= 0
            or self.height <= 0
        ):
            self.drops.clear()
            self.splashes.clear()
            self.reset_timing()
            return True

        alive = []

        for drop in self.drops:
            if (
                drop.x < 0
                or drop.x >= self.width
            ):
                drop.active = False
                continue

            if (
                drop.head_y - drop.length
                >= self.height
            ):
                drop.active = False
                continue

            if drop.redirect_target is not None and not (
                0
                <= drop.redirect_target
                < self.width
            ):
                drop.redirect_target = None

            alive.append(drop)

        self.drops = alive

        self.splashes = [
            splash
            for splash in self.splashes
            if 0 <= splash.x < self.width
            and 0 <= splash.y < self.height
        ]

        self.reset_timing()

        return True

    def close(self):
        self.drops.clear()
        self.splashes.clear()