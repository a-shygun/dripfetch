import calendar
from datetime import date

from ..base import BaseBox


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
    _GAP  = 1
    _DAYS_PER_WEEK = 7
    _GRID_WIDTH = _DAYS_PER_WEEK * _CELL + (_DAYS_PER_WEEK - 1) * _GAP  # = 20

    _VALID_STARTING_DAYS = {"monday", "sunday", "saturday"}

    # Day-name header row for each starting day.
    _DAY_NAMES = {
        "monday":   ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"),
        "saturday": ("Sa", "Su", "Mo", "Tu", "We", "Th", "Fr"),
        "sunday":   ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"),
    }

    # calendar module firstweekday values (0=Mon, 5=Sat, 6=Sun).
    _FIRST_WEEKDAY = {
        "monday":   0,
        "saturday": 5,
        "sunday":   6,
    }

    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)
        raw = config.get("starting_day", "monday")
        self._start = raw.lower() if isinstance(raw, str) else "monday"
        if self._start not in self._VALID_STARTING_DAYS:
            self._start = "monday"

    # ------------------------------------------------------------------
    # Plug-and-play config validator (called by config.py automatically)
    # ------------------------------------------------------------------
    @classmethod
    def validate_config(cls, item, path):
        from ...app.config import _string, _error  # noqa: PLC0415

        if "starting_day" in item:
            value = _string(item["starting_day"], f"{path}.starting_day")
            if value.lower() not in cls._VALID_STARTING_DAYS:
                _error(
                    f"{path}.starting_day",
                    f"must be one of: {', '.join(sorted(cls._VALID_STARTING_DAYS))}",
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _month_matrix(self, year, month):
        """Week-lists of date objects or None (None = outside target month)."""
        cal = calendar.Calendar(firstweekday=self._FIRST_WEEKDAY[self._start])
        return [
            [d if d.month == month else None for d in week]
            for week in cal.monthdatescalendar(year, month)
        ]

    # ------------------------------------------------------------------
    # BaseBox interface
    # ------------------------------------------------------------------
    def dimensions(self):
        today = date.today()
        weeks = self._month_matrix(today.year, today.month)
        return self._GRID_WIDTH, 4 + len(weeks)

    def draw_content(self, x, y, width, height):
        if width <= 0 or height <= 0:
            return

        today = date.today()
        year  = today.year
        month = today.month
        weeks = self._month_matrix(year, month)

        row = 0

        # ── Title: "September 2026" ──────────────────────────────────
        title = date(year, month, 1).strftime("%B %Y")
        self.renderer.draw(
            x + max(0, (self._GRID_WIDTH - len(title)) // 2),
            y + row,
            title[:width],
            self.colors.title,
        )
        row += 1

        # ── Separator ───────────────────────────────────────────────
        self.renderer.draw(x, y + row, "─" * min(width, self._GRID_WIDTH), self.colors.line)
        row += 1

        # ── Day names ───────────────────────────────────────────────
        for col, name in enumerate(self._DAY_NAMES[self._start]):
            cx = x + col * (self._CELL + self._GAP)
            if cx + self._CELL > x + width:
                break
            self.renderer.draw(cx, y + row, name, self.colors.line)
        row += 1

        # ── Separator ───────────────────────────────────────────────
        self.renderer.draw(x, y + row, "─" * min(width, self._GRID_WIDTH), self.colors.line)
        row += 1

        # ── Week rows ───────────────────────────────────────────────
        for week in weeks:
            if row >= height:
                break

            for col, day in enumerate(week):
                cx = x + col * (self._CELL + self._GAP)
                if cx + self._CELL > x + width:
                    break

                if day is None:
                    # Blank slot — day belongs to an adjacent month.
                    self.renderer.draw(cx, y + row, "  ", self.colors.body)
                    continue

                label = f"{day.day:2d}"

                if day == today:
                    self.renderer.draw(cx, y + row, label, self.colors.accent)
                else:
                    self.renderer.draw(cx, y + row, label, self.colors.body)

            row += 1