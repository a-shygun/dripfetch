from ...app.terminal import parse_color
from ..base import BaseBox
from .helper import validation
from .helper.logo_assets import detect_logo, load_logo
from .helper.logo_markup import parse_logo


class LogoBox(BaseBox):
    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)

        # An explicit config value wins; only use platform detection when
        # no logo was configured.
        self.logo = config.get("logo") or detect_logo() or ""

        configured_colors = config.get("colors")
        if configured_colors:
            self.logo_colors = [parse_color(color) for color in configured_colors]
        else:
            self.logo_colors = [
                self.colors.accent,
                self.colors.text,
                self.colors.border,
            ]

        self.lines = load_logo(self.logo)

    @classmethod
    def validate_config(cls, item, path):
        if "logo" in item:
            validation.string(item["logo"], f"{path}.logo")
        if "colors" in item:
            colors = item["colors"]
            colors_path = f"{path}.colors"
            if not isinstance(colors, list) or not colors:
                validation.error(colors_path, "must be a non-empty list of colors")
            for index, color in enumerate(colors):
                validation.color(color, f"{colors_path}[{index}]")

    def content(self):
        return parse_logo(self.lines, self.logo_colors, self.colors.text)
