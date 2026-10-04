from datetime import date

from ..base import BaseBox
from .helper import validation
from .helper.calendar_grid import (
    VALID_STARTING_DAYS,
    MonthGrid,
    normalize_starting_day,
)


class CalendarBox(BaseBox):
    """A monthly calendar box.

    Displays the current month with today's date highlighted.
    Days outside the current month are never shown.

    Config keys
    -----------
    starting_day : str   (default: "monday")
        Which day to put in the first column.
        Accepted values: "monday", "sunday", "saturday".
    """

    # 2-char day cells with 1-char gaps: 7*2 + 6*1 = 20 chars wide.
    _CELL = 2
    _GAP = 1
    _DAYS_PER_WEEK = 7
    _GRID_WIDTH = _DAYS_PER_WEEK * _CELL + (_DAYS_PER_WEEK - 1) * _GAP  # = 20

    # Title, rule, day names, rule.
    _HEADER_ROWS = 4

    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)
        self._grid = MonthGrid(normalize_starting_day(config.get("starting_day")))

    @classmethod
    def validate_config(cls, item, path):
        if "starting_day" in item:
            value = validation.string(item["starting_day"], f"{path}.starting_day")
            if value.lower() not in VALID_STARTING_DAYS:
                validation.error(
                    f"{path}.starting_day",
                    f"must be one of: {', '.join(sorted(VALID_STARTING_DAYS))}",
                )

    # ------------------------------------------------------------------
    # BaseBox interface
    # ------------------------------------------------------------------
    def dimensions(self):
        today = date.today()
        weeks = self._grid.weeks(today.year, today.month)
        return self._GRID_WIDTH, self._HEADER_ROWS + len(weeks)

    def draw_content(self, x, y, width, height):
        if width <= 0 or height <= 0:
            return

        today = date.today()
        weeks = self._grid.weeks(today.year, today.month)

        self._draw_title(x, y, width, today)
        self._draw_rule(x, y + 1, width)
        self._draw_day_names(x, y + 2, width)
        self._draw_rule(x, y + 3, width)

        for offset, week in enumerate(weeks):
            row = self._HEADER_ROWS + offset
            if row >= height:
                break
            self._draw_week(x, y + row, width, week, today)

    # ------------------------------------------------------------------
    # Drawing pieces
    # ------------------------------------------------------------------
    def _cell_x(self, x, column):
        return x + column * (self._CELL + self._GAP)

    def _draw_title(self, x, y, width, today):
        title = date(today.year, today.month, 1).strftime("%B %Y")
        self.renderer.draw(
            x + max(0, (self._GRID_WIDTH - len(title)) // 2),
            y,
            title[:width],
            self.colors.title,
        )

    def _draw_rule(self, x, y, width):
        self.renderer.draw(
            x, y, "─" * min(width, self._GRID_WIDTH), self.colors.line
        )

    def _draw_day_names(self, x, y, width):
        for column, name in enumerate(self._grid.day_names):
            cx = self._cell_x(x, column)
            if cx + self._CELL > x + width:
                break
            self.renderer.draw(cx, y, name, self.colors.line)

    def _draw_week(self, x, y, width, week, today):
        for column, day in enumerate(week):
            cx = self._cell_x(x, column)
            if cx + self._CELL > x + width:
                break

            if day is None:
                # Blank slot -- day belongs to an adjacent month.
                self.renderer.draw(cx, y, "  ", self.colors.body)
                continue

            color = self.colors.accent if day == today else self.colors.body
            self.renderer.draw(cx, y, f"{day.day:2d}", color)
