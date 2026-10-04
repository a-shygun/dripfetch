import threading
import time

from ..base import BaseBox
from .helper import validation
from .helper.forecast import fetch_forecast, format_row
from .helper.geolocation import resolve_location
from .helper.parsing import clamp_int


class WeatherBox(BaseBox):
    CACHE_TIME = 1800
    TIMEOUT = 10

    DEFAULT_DAYS = 5
    MIN_DAYS = 1
    MAX_DAYS = 7

    VALID_UNITS = {"celsius", "fahrenheit", "metric", "imperial"}
    _FAHRENHEIT_UNITS = {"fahrenheit", "imperial"}

    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)

        self.location = config.get("location", "")
        self.latitude = config.get("latitude")
        self.longitude = config.get("longitude")

        units = config.get("units", "celsius")
        self.units = units if units in self.VALID_UNITS else "celsius"
        fahrenheit = self.units in self._FAHRENHEIT_UNITS
        self.temperature_unit = "fahrenheit" if fahrenheit else "celsius"
        self.degree_letter = "F" if fahrenheit else "C"

        self.days_count = clamp_int(
            config.get("days", self.DEFAULT_DAYS),
            self.MIN_DAYS,
            self.MAX_DAYS,
            default=self.DEFAULT_DAYS,
        )

        self.location_name = self.location
        self.forecast = []
        self.error = None
        self.loading = True

        self.last_attempt = 0
        self.last_update = 0

        self._thread = None
        self._lock = threading.Lock()

        self._start_fetch()

    @classmethod
    def validate_config(cls, item, path):
        if "location" in item:
            validation.string(item["location"], f"{path}.location")
        if "latitude" in item:
            validation.number(item["latitude"], f"{path}.latitude")
        if "longitude" in item:
            validation.number(item["longitude"], f"{path}.longitude")
        if "units" in item:
            validation.enum(item["units"], f"{path}.units", cls.VALID_UNITS)
        if "days" in item:
            days = validation.integer(item["days"], f"{path}.days")
            if not cls.MIN_DAYS <= days <= cls.MAX_DAYS:
                validation.error(
                    f"{path}.days",
                    f"must be between {cls.MIN_DAYS} and {cls.MAX_DAYS}",
                )

    # ------------------------------------------------------------------
    # Background fetching
    # ------------------------------------------------------------------
    def _start_fetch(self):
        now = time.monotonic()

        if self._thread and self._thread.is_alive():
            return

        if now - self.last_attempt < self.CACHE_TIME:
            return

        self.last_attempt = now
        self.loading = True

        self._thread = threading.Thread(target=self._fetch, daemon=True)
        self._thread.start()

    def _fetch(self):
        try:
            latitude, longitude, location = resolve_location(
                self.latitude, self.longitude, self.location, self.TIMEOUT
            )
            forecast = fetch_forecast(
                latitude,
                longitude,
                self.temperature_unit,
                self.days_count,
                self.TIMEOUT,
            )

            with self._lock:
                self.forecast = forecast
                self.location_name = location
                self.error = None
                self.loading = False
                self.last_update = time.monotonic()

        except Exception as exc:
            with self._lock:
                self.error = str(exc)
                self.loading = False

        finally:
            # content() is cached by BaseBox (see base.py). This fetch runs
            # on a background thread and either outcome changes what
            # content() would return, so invalidate the cache either way.
            self.mark_dirty()

    def update(self):
        if time.monotonic() - self.last_update >= self.CACHE_TIME:
            self._start_fetch()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def content(self):
        with self._lock:
            forecast = list(self.forecast)
            loading = self.loading
            location = self.location_name

        if not forecast:
            text = "Fetching weather..." if loading else "Weather unavailable"
            return [[(text, self.colors.body)]]

        title = f"WEATHER / {location.upper()}"
        rows = [
            format_row(day, self.degree_letter)
            for day in forecast[: self.days_count]
        ]

        # Only as wide as the widest line actually needs -- no more,
        # no less -- so the separator (and the box border around it)
        # never ends up wider than the data it's framing.
        width = max(len(title), *(len(row) for row in rows))

        lines = [
            [(title, self.colors.title)],
            [("─" * width, self.colors.line)],
        ]
        lines.extend([(row, self.colors.body)] for row in rows)

        return lines
