from dataclasses import dataclass


@dataclass(frozen=True)
class RGBA:
    r: int
    g: int
    b: int
    a: int = 255


def get_rgb(color):
    color = color.lstrip("#")
    if len(color) == 6:
        color += "FF"
    if len(color) != 8:
        raise ValueError(f"Invalid color: #{color}")
    try:
        return RGBA(
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
            int(color[6:8], 16),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid color: #{color}") from exc


class ColorManager:
    def __init__(self):
        self.colors = {}

    def create_pairs(self, colors, background=None):
        self.colors = {color: get_rgb(color) for color in colors}

    def attribute(self, color, tail, length):
        base = self.colors.get(color, get_rgb("#FFFFFF"))
        brightness = (
            1.0
            if length <= 1
            else max(
                0.0,
                min(1.0, 1 - tail / (length - 1)),
            )
        )
        return RGBA(
            round(base.r * brightness),
            round(base.g * brightness),
            round(base.b * brightness),
            base.a,
        )
