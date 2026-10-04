"""Month grid data for the calendar box."""

import calendar

DEFAULT_STARTING_DAY = "monday"
VALID_STARTING_DAYS = {"monday", "sunday", "saturday"}

# Day-name header row for each starting day.
DAY_NAMES = {
    "monday": ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"),
    "saturday": ("Sa", "Su", "Mo", "Tu", "We", "Th", "Fr"),
    "sunday": ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"),
}

# calendar module firstweekday values (0=Mon, 5=Sat, 6=Sun).
FIRST_WEEKDAY = {
    "monday": 0,
    "saturday": 5,
    "sunday": 6,
}


def normalize_starting_day(raw):
    value = raw.lower() if isinstance(raw, str) else DEFAULT_STARTING_DAY
    return value if value in VALID_STARTING_DAYS else DEFAULT_STARTING_DAY


class MonthGrid:
    """Week rows of date objects (None = outside the month), cached per month.

    The grid only changes once a month, but dimensions() and draw_content()
    ask for it many times a second, so rebuild it only when (year, month)
    changes.
    """

    def __init__(self, starting_day):
        self.starting_day = starting_day
        self._key = None
        self._weeks = None

    @property
    def day_names(self):
        return DAY_NAMES[self.starting_day]

    def weeks(self, year, month):
        key = (year, month)
        if key != self._key:
            self._key = key
            self._weeks = self._build(year, month)
        return self._weeks

    def _build(self, year, month):
        cal = calendar.Calendar(firstweekday=FIRST_WEEKDAY[self.starting_day])
        return [
            [d if d.month == month else None for d in week]
            for week in cal.monthdatescalendar(year, month)
        ]
