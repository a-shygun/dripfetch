import random
import time
from collections import deque
from dataclasses import dataclass, field

from ..app.terminal import RGBA, parse_color

BOX_PADDING = 2
SPAWN_INTERVAL = 5


@dataclass
class Drop:
    x: int
    head_y: int = -1
    speed: float = 50
    length: int = 5
    color: str = "#FFFFFF"
    character: str = "│"
    path: deque = field(default_factory=deque)
    redirect_target: int | None = None
    active: bool = True
    last_move: float = field(
        default_factory=time.monotonic
    )


class ColorManager:
    def __init__(self):
        self.colors = {}

    def create_pairs(self, colors):
        self.colors = {
            color: parse_color(color)
            for color in colors
        }

    def attribute(self, color, tail, length):
        base = self.colors.get(
            color,
            parse_color("#FFFFFF"),
        )

        brightness = 1.0 if length <= 1 else max(0.0, min(1.0, 1 - tail / (length - 1)))

        return RGBA(
            round(base.r * brightness),
            round(base.g * brightness),
            round(base.b * brightness),
            base.a,
        )


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
        self.colors = ColorManager()

        self.paused_at = None
        self.spawned = 0
        self.spawned_at = time.monotonic()

        rain = config.get("rain", {})

        self.collision = rain.get(
            "collision",
            True,
        )

        self.intensity = max(
            0,
            float(rain.get("intensity", 1)),
        )

        self.characters = rain.get(
            "character",
            "│",
        )

        self.speeds = rain.get(
            "speeds",
            [],
        )

        self.lengths = rain.get(
            "lengths",
            [],
        )

        self.rain_colors = rain.get(
            "colors",
            [],
        )

        colors = dict.fromkeys(
            color
            for _, color in self.rain_colors
        )

        self.colors.create_pairs(
            colors or ["#FFFFFF"]
        )

    # ------------------------------------------------------------------
    # Collision
    # ------------------------------------------------------------------

    def _collision(
        self,
        x,
        old_y,
        new_y,
        bounds,
    ):
        if not self.collision:
            return None

        for (
            left,
            top,
            right,
            bottom,
        ) in bounds:
            if (
                old_y < top <= new_y
                and left <= x <= right
            ):
                targets = (
                    max(
                        0,
                        left - BOX_PADDING,
                    ),
                    min(
                        self.width - 1,
                        right + BOX_PADDING,
                    ),
                )

                target = min(
                    targets,
                    key=lambda value: abs(x - value),
                )

                return target, top

        return None

    @staticmethod
    def _inside_box(x, y, bounds):
        return any(
            left <= x <= right
            and top <= y <= bottom
            for (
                left,
                top,
                right,
                bottom,
            ) in bounds
        )

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    @staticmethod
    def _choose(values, default):
        if not values:
            return default

        return random.choices(
            [value for _, value in values],
            [weight for weight, _ in values],
        )[0]

    @staticmethod
    def _choose_character(characters):
        if isinstance(characters, str):
            return characters

        if not characters:
            return "│"

        return random.choice(characters)

    def _new_drop(self):
        if self.width <= 0:
            return None

        length = max(
            1,
            int(
                self._choose(
                    self.lengths,
                    5,
                )
            ),
        )

        return Drop(
            x=random.randrange(self.width),
            head_y=-1,
            speed=max(
                1,
                float(
                    self._choose(
                        self.speeds,
                        50,
                    )
                ),
            ),
            length=length,
            color=self._choose(
                self.rain_colors,
                "#FFFFFF",
            ),
            character=self._choose_character(
                self.characters
            ),
            path=deque(maxlen=length),
        )

    def _spawn(self, now):
        if not self.intensity or not self.width:
            self.spawned_at = now
            return

        elapsed = min(
            now - self.spawned_at,
            0.25,
        )

        self.spawned_at = now
        self.spawned += (
            elapsed
            * self.intensity
            / SPAWN_INTERVAL
        )

        count = int(self.spawned)
        self.spawned -= count

        for _ in range(count):
            drop = self._new_drop()

            if drop is not None:
                self.drops.append(drop)

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def _move_horizontal(self, drop):
        target = drop.redirect_target

        if target is None:
            return

        direction = (
            1 if target > drop.x else -1
        )

        drop.x += direction

        if drop.character in ("│", "|"):
            drop.path.append(
                (
                    drop.x,
                    drop.head_y,
                    "─",
                )
            )

            if drop.x == target:
                drop.path[-1] = (
                    drop.x,
                    drop.head_y,
                    "┐"
                    if direction > 0
                    else "┌",
                )

                drop.redirect_target = None

            return

        drop.path.append(
            (
                drop.x,
                drop.head_y,
                drop.character,
            )
        )

        if drop.x == target:
            drop.redirect_target = None

    def _move_down(self, drop, bounds):
        old_x = drop.x
        old_y = drop.head_y

        hit = self._collision(
            old_x,
            old_y,
            old_y + 1,
            bounds,
        )

        if hit:
            target, top = hit

            drop.head_y = top - 1
            drop.redirect_target = target

            if drop.character in ("│", "|"):
                corner = (
                    "└"
                    if target > old_x
                    else "┘"
                )

                if drop.path:
                    drop.path[-1] = (
                        old_x,
                        drop.head_y,
                        corner,
                    )
                else:
                    drop.path.append(
                        (
                            old_x,
                            drop.head_y,
                            corner,
                        )
                    )

            return

        drop.head_y += 1

        drop.path.append(
            (
                drop.x,
                drop.head_y,
                drop.character,
            )
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update_drop(
        self,
        drop,
        now,
        bounds,
    ):
        if not drop.active:
            return

        interval = max(
            1.0,
            float(drop.speed),
        ) / 1000

        elapsed = now - drop.last_move

        if elapsed < interval:
            return

        steps = min(
            max(
                1,
                int(elapsed / interval),
            ),
            8,
        )

        for _ in range(steps):
            if drop.redirect_target is None:
                self._move_down(
                    drop,
                    bounds,
                )
            else:
                self._move_horizontal(
                    drop
                )

            if (
                drop.head_y - drop.length
                >= self.height
            ):
                drop.active = False
                break

        drop.last_move = now

    def update(self):
        now = time.monotonic()
        bounds = (
            self.box.get_box_bounds_list()
        )

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

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw_drop(self, drop, bounds):
        if not drop.active:
            return

        for tail, (
            x,
            y,
            character,
        ) in enumerate(
            reversed(drop.path)
        ):
            if tail >= drop.length:
                break

            if not (
                0 <= x < self.width
                and 0 <= y < self.height
            ):
                continue

            if (
                not self.collision
                and self._inside_box(
                    x,
                    y,
                    bounds,
                )
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

    def draw(self):
        bounds = (
            self.box.get_box_bounds_list()
        )

        for drop in self.drops:
            self._draw_drop(
                drop,
                bounds,
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

        self.spawned_at += delay
        self.paused_at = None

    def reset_timing(self):
        now = time.monotonic()

        for drop in self.drops:
            drop.last_move = now

        self.spawned_at = now
        self.spawned = 0

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
        self.reset_timing()

        return True

    def close(self):
        self.drops.clear()