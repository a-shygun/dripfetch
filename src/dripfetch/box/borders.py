class Border:
    TYPES = {
        "single": ("─", "│", "┌", "┐", "└", "┘"),
        "double": ("═", "║", "╔", "╗", "╚", "╝"),
    }

    def __init__(self, name="single"):
        self.name = name if name in self.TYPES else "single"

    @property
    def characters(self):
        return self.TYPES[self.name]

    @property
    def side_width(self):
        return 1

    def dimensions(self, width, height, horizontal, vertical):
        return width + horizontal * 2 + 2, height + vertical * 2 + 2

    def draw(self, renderer, x, y, width, height, color, selected=False):
        top, side, tl, tr, bl, br = self.characters
        corner = "*" if selected else tl

        renderer.draw(
            x,
            y,
            corner + top * (width - 2) + tr,
            color,
        )

        renderer.draw(
            x,
            y + height - 1,
            bl + top * (width - 2) + br,
            color,
        )

        for row in range(y + 1, y + height - 1):
            renderer.draw(x, row, side, color)
            renderer.draw(x + width - 1, row, side, color)
