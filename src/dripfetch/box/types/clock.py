import time

from ..base import BaseBox
from .helper import validation
from .helper.clock_layout import ClockOptions, build_geometry


class ClockBox(BaseBox):
    _VALID_STYLES = {"single", "double"}
    _VALID_SIZES = {"small", "medium", "big"}
    _BOOLEAN_KEYS = (
        "clock_24h",
        "show_seconds",
        "show_am_pm",
        "blink_colon",
        "show_date",
    )

    def __init__(self, stdscr, config, boxes_config, colors, renderer):
        super().__init__(stdscr, config, boxes_config, colors, renderer)
        self.options = ClockOptions.from_config(config)

        # Building the geometry reformats the time and rebuilds every glyph
        # pattern, but the display only changes once a second (digits and
        # the blinking colon both flip on second boundaries), so cache it.
        self._geometry_key = None
        self._geometry_cache = None

    @classmethod
    def validate_config(cls, item, path):
        if "clock_style" in item:
            validation.enum(item["clock_style"], f"{path}.clock_style", cls._VALID_STYLES)
        if "clock_size" in item:
            validation.enum(item["clock_size"], f"{path}.clock_size", cls._VALID_SIZES)
        for key in cls._BOOLEAN_KEYS:
            if key in item:
                validation.boolean(item[key], f"{path}.{key}")

    def _cached_geometry(self):
        now = time.localtime()
        key = (now.tm_hour, now.tm_min, now.tm_sec)
        if key != self._geometry_key:
            self._geometry_key = key
            self._geometry_cache = build_geometry(now, self.options)
        return self._geometry_cache

    def dimensions(self):
        geometry = self._cached_geometry()
        return geometry.content_width, geometry.content_height

    def draw_content(self, x, y, width, height):
        geometry = self._cached_geometry()
        x_start = x + max(0, (width - geometry.width) // 2)
        y_start = y + max(0, (height - geometry.content_height) // 2)

        offset = 0
        for char, pattern in zip(geometry.text, geometry.patterns):
            color = self.colors.accent if char == ":" else self.colors.text
            for row, line in enumerate(pattern):
                self.renderer.draw(x_start + offset, y_start + row, line, color)
            offset += len(pattern[0]) + geometry.spacing

        if geometry.date:
            date_x = x + max(0, (width - len(geometry.date)) // 2)
            self.renderer.draw(
                date_x,
                y_start + geometry.height + 1,
                geometry.date,
                self.colors.text,
            )
