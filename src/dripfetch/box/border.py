class Border:
    TYPES = {
        "single": ("─", "│", "┌", "┐", "└", "┘"),
        "double": ("═", "║", "╔", "╗", "╚", "╝"),
        "none": ("", "", "", "", "", ""),
        # Titled variants keep only the top and bottom rules; the title is
        # embedded in the top rule without side walls.
        "titled_single": ("─", "", "┌", "┐", "└", "┘"),
        "titled_double": ("═", "", "╔", "╗", "╚", "╝"),
    }

    def __init__(self, name="single"):
        self.name = name if name in self.TYPES else "single"

    @property
    def characters(self):
        return self.TYPES[self.name]

    @property
    def visible(self):
        return self.name != "none"

    def dimensions(self, width, height, horizontal, vertical):
        return (
            width + horizontal * 2 + 2,
            height + vertical * 2 + 2,
        )

    def draw(
        self,
        renderer,
        x,
        y,
        width,
        height,
        color,
        selected=False,
        title=None,
    ):
        if not self.visible:
            return
        (
            top,
            side,
            top_left,
            top_right,
            bottom_left,
            bottom_right,
        ) = self.characters
        if selected:
            top_left = "*"
        top_line = top_left + top * (width - 2) + top_right
        if title:
            top_line = self._embed_title(top_line, title)
        renderer.draw(
            x,
            y,
            top_line,
            color,
        )
        renderer.draw(
            x,
            y + height - 1,
            bottom_left + top * (width - 2) + bottom_right,
            color,
        )
        # Titled types have no side character, so there is nothing to draw
        # down the left/right edges.
        if not side:
            return
        for row in range(y + 1, y + height - 1):
            renderer.draw(
                x,
                row,
                side,
                color,
            )
            renderer.draw(
                x + width - 1,
                row,
                side,
                color,
            )

    @staticmethod
    def _embed_title(line, title):
        # Splice the title into the middle of an already-built border
        # line, leaving the outermost character (corner glyph) on each
        # side untouched, and never growing/shrinking the line. The
        # title gets a 1-character pad on each side.
        width = len(line)
        if width <= 2:
            return line
        title = f" {title} "
        title = title[: width - 2]
        if not title.strip():
            return line
        start = 1 + max(0, (width - 2 - len(title)) // 2)
        end = start + len(title)
        if end > width - 1:
            end = width - 1
            start = end - len(title)
        return line[:start] + title + line[end:]
