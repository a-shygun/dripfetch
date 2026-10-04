import random
import time
from collections import deque

from .constants import SPAWN_INTERVAL
from .models import Drop


class Spawner:
    """Owns everything needed to decide *when* and *what* to spawn.

    Kept separate from Rain so the weighted-choice / timing bookkeeping
    can be read (and changed) without the movement, collision, or
    drawing code getting in the way.
    """

    def __init__(self, rain_config):
        self.characters = rain_config.get(
            "character",
            "│",
        )
        self.speeds = rain_config.get(
            "speeds",
            [],
        )
        self.lengths = rain_config.get(
            "lengths",
            [],
        )
        self.rain_colors = rain_config.get(
            "colors",
            [],
        )
        self.intensity = max(
            0,
            float(rain_config.get("intensity", 1)),
        )

        self.spawned = 0
        self.spawned_at = time.monotonic()

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

    def new_drop(self, width):
        if width <= 0:
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

        speed = max(
            1,
            float(
                self._choose(
                    self.speeds,
                    50,
                )
            ),
        )

        return Drop(
            x=random.randrange(width),
            head_y=-1,
            speed=speed,
            length=length,
            color=self._choose(
                self.rain_colors,
                "#FFFFFF",
            ),
            character=self._choose_character(
                self.characters
            ),
            path=deque(maxlen=length),
            base_speed=speed,
        )

    def spawn(self, now, width):
        """Return the list of newly-spawned drops for this tick."""
        if not self.intensity or not width:
            self.spawned_at = now
            return []

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

        drops = []

        for _ in range(count):
            drop = self.new_drop(width)

            if drop is not None:
                drops.append(drop)

        return drops

    def reset_timing(self, now):
        self.spawned_at = now
        self.spawned = 0