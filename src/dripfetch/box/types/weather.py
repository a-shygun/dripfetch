import json
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

from ..base import BaseBox


class WeatherBox(BaseBox):
    WIDTH = 40
    HEIGHT = 7
    CACHE_TIME = 1800
    TIMEOUT = 10

    CODES = {
        0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Cloudy",
        45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
        56: "Freezing Drizzle", 57: "Freezing Drizzle", 61: "Light Rain",
        63: "Rain", 65: "Heavy Rain", 66: "Freezing Rain", 67: "Heavy Rain",
        71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains",
        80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
        85: "Snow Showers", 86: "Heavy Snow", 95: "Thunderstorm",
        96: "Thunderstorm", 99: "Thunderstorm",
    }

    def __init__(self, stdscr, config, boxes, colors, renderer=None):
        super().__init__(stdscr, config, boxes, colors, renderer)
        self.location = config.get("location", "")
        self.latitude = config.get("latitude")
        self.longitude = config.get("longitude")
        self.location_name = self.location
        self.days = []
        self.error = None
        self.loading = True
        self.last_attempt = 0
        self.last_update = 0
        self._thread = None
        self._lock = threading.Lock()
        self._start_fetch()

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

    def _geocode(self):
        if self.latitude is not None and self.longitude is not None:
            return float(self.latitude), float(self.longitude), self.location
        if not self.location:
            raise ValueError("No location configured")

        query = urllib.parse.urlencode({
            "name": self.location,
            "count": 1,
            "language": "en",
            "format": "json",
        })

        with urllib.request.urlopen(
            f"https://geocoding-api.open-meteo.com/v1/search?{query}",
            timeout=self.TIMEOUT,
        ) as response:
            results = json.load(response).get("results", [])

        if not results:
            raise ValueError(f"Location not found: {self.location}")

        result = results[0]
        name = result.get("name", self.location)
        country = result.get("country", "")
        return result["latitude"], result["longitude"], f"{name}, {country}".strip(", ")

    def _fetch(self):
        try:
            latitude, longitude, location = self._geocode()
            params = urllib.parse.urlencode({
                "latitude": latitude,
                "longitude": longitude,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 5,
            })

            with urllib.request.urlopen(
                f"https://api.open-meteo.com/v1/forecast?{params}",
                timeout=self.TIMEOUT,
            ) as response:
                daily = json.load(response)["daily"]

            days = []
            for i, value in enumerate(daily["time"]):
                date = datetime.fromisoformat(value)
                days.append({
                    "day": "Today" if i == 0 else date.strftime("%a"),
                    "condition": self.CODES.get(daily["weather_code"][i], "Unknown"),
                    "high": self._value(daily["temperature_2m_max"][i]),
                    "low": self._value(daily["temperature_2m_min"][i]),
                    "rain": self._value(daily["precipitation_probability_max"][i]),
                })

            with self._lock:
                self.days = days
                self.location_name = location
                self.error = None
                self.loading = False
                self.last_update = time.monotonic()

        except Exception as exc:
            with self._lock:
                self.error = str(exc)
                self.loading = False

    @staticmethod
    def _value(value):
        return "--" if value is None else str(round(value))

    def update(self):
        if time.monotonic() - self.last_update >= self.CACHE_TIME:
            self._start_fetch()

    def _format(self, day):
        condition = day["condition"][:14]
        return f"{day['day']:<6} {condition:<14} {day['high']:>2}°/{day['low']:<2}° {day['rain']:>3}%"

    def draw_content(self, x, y, width, height):
        if width <= 0 or height <= 0:
            return

        with self._lock:
            days = list(self.days)
            loading = self.loading
            location = self.location_name

        if not days:
            text = "Fetching weather..." if loading else "Weather unavailable"
            self.renderer.draw(x, y, text[:width], self.colors.body)
            return

        self.renderer.draw(
            x, y,
            f"WEATHER / {location.upper()}"[:width],
            self.colors.title,
        )

        if height < 2:
            return

        self.renderer.draw(
            x, y + 1,
            "─" * min(width, self.WIDTH),
            self.colors.line,
        )

        if height < 3:
            return

        self.renderer.draw(
            x, y + 2,
            f"{'DAY':<6} {'CONDITION':<14} {'TEMP':>5} {'RAIN':>4}"[:width],
            self.colors.line,
        )

        for row, day in enumerate(days[:5], 3):
            if row >= height:
                break
            self.renderer.draw(
                x, y + row,
                self._format(day)[:width],
                self.colors.body,
            )

    def dimensions(self):
        return self.WIDTH, self.HEIGHT