import platform
import re
from importlib.resources import files

from ...terminal import parse_color
from ..base import BaseBox


class LogoBox(BaseBox):
    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)
        self.config_logo = config.get("logo", "")
        self.logo = self._detect_logo() or self.config_logo
        self.logo_colors = [parse_color(color) for color in config.get("colors", [])]
        self.lines = self._load_logo()
        self.parsed_lines = [self._parse_line(line) for line in self.lines]

    def _detect_logo(self):
        system = platform.system()

        if system == "Darwin":
            return self._find_logo("macos")

        if system == "Windows":
            return self._find_logo("windows")

        if system == "Linux":
            distro = self._linux_distro()
            return self._find_logo(distro) if distro else None

        return None

    def _linux_distro(self):
        try:
            with open("/etc/os-release", encoding="utf-8") as file:
                data = {}

                for line in file:
                    key, _, value = line.partition("=")
                    data[key] = value.strip().strip('"')

            return data.get("ID", "").lower()
        except (FileNotFoundError, OSError):
            return None

    def _find_logo(self, name):
        if not name:
            return None

        path = files("dripfetch").joinpath("assets", "logos", f"{name}.txt")

        if path.is_file():
            return name

        return None

    def _load_logo(self):
        path = files("dripfetch").joinpath("assets", "logos", f"{self.logo}.txt")

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
                color = (
                    self.logo_colors[index]
                    if 0 <= index < len(self.logo_colors)
                    else None
                )
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