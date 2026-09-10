import re
from importlib.resources import files

from ...terminal import parse_color
from ..base import BaseBox


class LogoBox(BaseBox):
    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)
        self.logo = config.get("logo", "")
        self.logo_colors = [parse_color(color) for color in config.get("colors", [])]
        self.lines = self._load_logo()
        self.parsed_lines = [self._parse_line(line) for line in self.lines]

    def _load_logo(self):
        path = files("dripfetch").joinpath("assets", "logos", f"{self.logo}.txt")
        print(f"LOGO: {self.logo}")
        print(f"PATH: {path}")
        print(f"EXISTS: {path.is_file()}")
        if not path.is_file():
            return []
        return path.read_text(encoding="utf-8").splitlines()
    def _parse_line(self, line):
        parts = re.split(r"(\$\d+)", line)
        color = None
        result = []

        for part in parts:
            if not part:
                continue

            if part.startswith("$"):
                index = int(part[1:]) - 1
                color = self.logo_colors[index] if 0 <= index < len(self.logo_colors) else None
                continue

            result.append((part, color))

        return result

    def draw_content(self, x, y, width, height):
        for row, segments in enumerate(self.parsed_lines):
            if row >= height:
                break

            offset = 0

            for text, color in segments:
                if offset >= width:
                    break

                text = text[:width - offset]
                self.renderer.draw(x + offset, y + row, text, color)
                offset += len(text)

    def dimensions(self):
        width = max(
            (sum(len(text) for text, _ in line) for line in self.parsed_lines),
            default=0,
        )
        return width, len(self.parsed_lines)