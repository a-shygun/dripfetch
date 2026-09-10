import random
from collections import deque

from .drop import Drop

SPAWN_INTERVAL = 5


def choose(values, default):
    if not values:
        return default
    return random.choices(
        [value for _, value in values],
        [weight for weight, _ in values],
    )[0]


def new_drop(width, speeds, lengths, rain_colors):
    if width <= 0:
        return None
    length = max(1, int(choose(lengths, 5)))
    return Drop(
        x=random.randrange(width),
        head_y=-1,
        speed=max(1, float(choose(speeds, 50))),
        length=length,
        color=choose(rain_colors, "#FFFFFF"),
        path=deque(maxlen=length),
    )


def spawn(
    drops,
    width,
    intensity,
    spawned,
    spawned_at,
    now,
    speeds,
    lengths,
    rain_colors,
):
    if not intensity or not width:
        return spawned, now
    elapsed = min(now - spawned_at, 0.25)
    spawned_at = now
    spawned += elapsed * intensity / SPAWN_INTERVAL
    count = int(spawned)
    spawned -= count
    for _ in range(count):
        drop = new_drop(
            width,
            speeds,
            lengths,
            rain_colors,
        )
        if drop is not None:
            drops.append(drop)
    return spawned, spawned_at
