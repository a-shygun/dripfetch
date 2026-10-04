import time

from ..app.terminal import RGBA, parse_color
from .constants import SPLASH_DURATION
from .physics import inside_box


def draw_drop(renderer, drop, bounds, width, height, collision_enabled, colors, background):
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
            0 <= x < width
            and 0 <= y < height
        ):
            continue

        if (
            not collision_enabled
            and inside_box(
                x,
                y,
                bounds,
            )
        ):
            continue

        renderer.draw(
            x,
            y,
            character,
            colors.attribute(
                drop.color,
                tail,
                drop.length,
                background,
            ),
        )


def draw_splashes(renderer, splashes, width, height, background):
    if not splashes:
        return

    now = time.monotonic()
    base = parse_color("#FFFFFF")

    for splash in splashes:
        if not (
            0 <= splash.x < width
            and 0 <= splash.y < height
        ):
            continue

        age = now - splash.born

        if age >= SPLASH_DURATION:
            continue

        fade = max(0.0, 1 - age / SPLASH_DURATION)

        # Same background-relative fade as drops: a fresh splash is
        # full white, and as it ages it blends into the background
        # color instead of fading to black.
        renderer.draw(
            splash.x,
            splash.y,
            splash.character,
            RGBA(
                round(background.r + (base.r - background.r) * fade),
                round(background.g + (base.g - background.g) * fade),
                round(background.b + (base.b - background.b) * fade),
                base.a,
            ),
        )