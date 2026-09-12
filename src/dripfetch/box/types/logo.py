import platform
import re
from importlib.resources import files

from ...app.terminal import parse_color
from ..manager import BaseBox


class LogoBox(BaseBox):
    def __init__(
        self,
        stdscr,
        config,
        boxes,
        colors,
        renderer,
    ):
        super().__init__(
            stdscr,
            config,
            boxes,
            colors,
            renderer,
        )

        self.logo = (
            self._detect_logo()
            or config.get("logo", "")
        )

        self.logo_colors = [
            parse_color(color)
            for color in config.get("colors", [])
        ]

        self.lines = self._load_logo()

    def content(self):
        content = []
        color = None

        for line in self.lines:
            parsed_line, color = self._parse_line(
                line,
                color,
            )
            content.append(parsed_line)

        return content

    def _detect_logo(self):
        system = platform.system()

        if system == "Darwin":
            return self._find_logo("macos")

        if system == "Windows":
            return self._find_logo("windows")

        if system == "Linux":
            distro = self._linux_distro()

            if distro:
                return self._find_logo(distro)

        return None

    def _linux_distro(self):
        try:
            with open(
                "/etc/os-release",
                encoding="utf-8",
            ) as file:
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

        path = files("dripfetch").joinpath(
            "assets",
            "logos",
            f"{name}.txt",
        )

        if path.is_file():
            return name

        return None

    def _load_logo(self):
        path = files("dripfetch").joinpath(
            "assets",
            "logos",
            f"{self.logo}.txt",
        )

        if not path.is_file():
            return []

        return path.read_text(
            encoding="utf-8"
        ).splitlines()

    def _parse_line(self, line, color):
        parts = re.split(
            r"(\$\d+)",
            line,
        )

        result = []

        for part in parts:
            if not part:
                continue

            if part.startswith("$"):
                index = int(part[1:]) - 1

                if 0 <= index < len(self.logo_colors):
                    color = self.logo_colors[index]
                else:
                    color = None

                continue

            result.append((part, color))

        return result, color