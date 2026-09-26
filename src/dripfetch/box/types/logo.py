import platform
import re
from importlib.resources import files

from ...app.terminal import parse_color
from ..base import BaseBox


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

        # An explicit config value wins; only use platform detection when
        # no logo was configured.
        self.logo = config.get("logo") or self._detect_logo() or ""

        configured_colors = config.get("colors")
        if configured_colors:
            self.logo_colors = [parse_color(color) for color in configured_colors]
        else:
            self.logo_colors = [
                self.colors.accent,
                self.colors.text,
                self.colors.border,
            ]

        self.lines = self._load_logo()

    # ------------------------------------------------------------------
    # Plug-and-play config validator (called by config.py automatically)
    # ------------------------------------------------------------------
    @classmethod
    def validate_config(cls, item, path):
        from ...app.config import _color, _error, _string  # noqa: PLC0415

        if "logo" in item:
            _string(item["logo"], f"{path}.logo")
        if "colors" in item:
            colors = item["colors"]
            colors_path = f"{path}.colors"
            if not isinstance(colors, list) or not colors:
                _error(colors_path, "must be a non-empty list of colors")
            for index, color in enumerate(colors):
                _color(color, f"{colors_path}[{index}]")

    def content(self):
        content = []
        color = self.colors.text

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

                color = self.logo_colors[index % len(self.logo_colors)]

                continue

            result.append((part, color))

        return result, color
