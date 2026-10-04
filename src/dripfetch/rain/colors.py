from ..app.terminal import RGBA, parse_color


class ColorManager:
    def __init__(self):
        self.colors = {}

    def create_pairs(self, colors):
        self.colors = {
            color: parse_color(color)
            for color in colors
        }

    def attribute(self, color, tail, length, background):
        base = self.colors.get(
            color,
            parse_color("#FFFFFF"),
        )

        brightness = 1.0 if length <= 1 else max(0.0, min(1.0, 1 - tail / (length - 1)))

        # Fade toward the configured background color rather than
        # toward black, so a drop's tail blends into the canvas behind
        # it instead of always sinking to darkness -- this matters for
        # light/white backgrounds, where fading to black looks like the
        # tail is punching a hole in the scene.
        return RGBA(
            round(background.r + (base.r - background.r) * brightness),
            round(background.g + (base.g - background.g) * brightness),
            round(background.b + (base.b - background.b) * brightness),
            base.a,
        )