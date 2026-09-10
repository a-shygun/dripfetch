from ..base import BaseBox


class TextBox(BaseBox):
    def _lines(self):
        return str(self.config.get("text", "")).splitlines()

    def dimensions(self):
        lines = self._lines()
        return max((len(line) for line in lines), default=0), len(lines)

    def draw_content(self, x, y, width, height):
        for index, line in enumerate(self._lines()[:height]):
            line = line[:width]
            column = x + max(0, (width - len(line)) // 2)
            self.renderer.draw(column, y + index, line, self.colors.text)
