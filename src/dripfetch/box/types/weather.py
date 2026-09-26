import json
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

from ..base import BaseBox


class WeatherBox(BaseBox):
    CACHE_TIME = 1800
    TIMEOUT = 10

    DEFAULT_DAYS = 5
    MIN_DAYS = 1
    MAX_DAYS = 7

    VALID_UNITS = {"celsius", "fahrenheit", "metric", "imperial"}
    _FAHRENHEIT_UNITS = {"fahrenheit", "imperial"}

    # A few country codes people expect to see written a bit differently
    # than the bare ISO 3166-1 alpha-2 code an API hands back.
    _COUNTRY_OVERRIDES = {
        "US": "USA",
        "GB": "UK",
    }

    CODES = {
        0: "Clear",
        1: "Mostly Clear",
        2: "Partly Cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Heavy Drizzle",
        56: "Freezing Drizzle",
        57: "Freezing Drizzle",
        61: "Light Rain",
        63: "Rain",
        65: "Heavy Rain",
        66: "Freezing Rain",
        67: "Heavy Rain",
        71: "Light Snow",
        73: "Snow",
        75: "Heavy Snow",
        77: "Snow Grains",
        80: "Light Showers",
        81: "Showers",
        82: "Heavy Showers",
        85: "Snow Showers",
        86: "Heavy Snow",
        95: "Thunderstorm",
        96: "Thunderstorm",
        99: "Thunderstorm",
    }

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

        self.location = config.get(
            "location",
            "",
        )
        self.latitude = config.get("latitude")
        self.longitude = config.get("longitude")

        units = config.get("units", "celsius")
        self.units = units if units in self.VALID_UNITS else "celsius"
        self.temperature_unit = (
            "fahrenheit"
            if self.units in self._FAHRENHEIT_UNITS
            else "celsius"
        )
        self.degree_letter = "F" if self.temperature_unit == "fahrenheit" else "C"

        self.days_count = self._clamp_days(
            config.get("days", self.DEFAULT_DAYS)
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
    def _clamp_days(cls, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            return cls.DEFAULT_DAYS
        return max(cls.MIN_DAYS, min(cls.MAX_DAYS, value))

    @classmethod
    def _short_country(cls, code):
        code = (code or "").strip().upper()
        if not code:
            return ""
        return cls._COUNTRY_OVERRIDES.get(code, code)

    @classmethod
    def _place(cls, city, country_code):
        city = (city or "").strip()
        country = cls._short_country(country_code)
        return f"{city}, {country}".strip(", ") or "Unknown"

    # ------------------------------------------------------------------
    # Plug-and-play config validator (called by config.py automatically)
    # ------------------------------------------------------------------
    @classmethod
    def validate_config(cls, item, path):
        from ...app.config import _enum, _integer, _number, _string  # noqa: PLC0415

        if "location" in item:
            _string(item["location"], f"{path}.location")
        if "latitude" in item:
            _number(item["latitude"], f"{path}.latitude")
        if "longitude" in item:
            _number(item["longitude"], f"{path}.longitude")
        if "units" in item:
            _enum(item["units"], f"{path}.units", cls.VALID_UNITS)
        if "days" in item:
            days = _integer(item["days"], f"{path}.days")
            if not cls.MIN_DAYS <= days <= cls.MAX_DAYS:
                from ...app.config import _error  # noqa: PLC0415

                _error(
                    f"{path}.days",
                    f"must be between {cls.MIN_DAYS} and {cls.MAX_DAYS}",
                )

    def _start_fetch(self):
        now = time.monotonic()

        if (
            self._thread
            and self._thread.is_alive()
        ):
            return

        if now - self.last_attempt < self.CACHE_TIME:
            return

        self.last_attempt = now
        self.loading = True

        self._thread = threading.Thread(
            target=self._fetch,
            daemon=True,
        )
        self._thread.start()

    def _geocode(self):
        if (
            self.latitude is not None
            and self.longitude is not None
        ):
            return (
                float(self.latitude),
                float(self.longitude),
                self.location,
            )

        if self.location:
            return self._geocode_location()

        return self._geolocate_by_ip()

    def _geocode_location(self):
        query = urllib.parse.urlencode(
            {
                "name": self.location,
                "count": 1,
                "language": "en",
                "format": "json",
            }
        )

        with urllib.request.urlopen(
            (
                "https://geocoding-api.open-meteo.com/"
                f"v1/search?{query}"
            ),
            timeout=self.TIMEOUT,
        ) as response:
            results = json.load(response).get(
                "results",
                [],
            )

        if not results:
            raise ValueError(
                f"Location not found: {self.location}"
            )

        result = results[0]

        location = self._place(
            result.get("name", self.location),
            result.get("country_code", ""),
        )

        return (
            result["latitude"],
            result["longitude"],
            location,
        )

    def _geolocate_by_ip(self):
        # No location or coordinates configured -- fall back to guessing
        # the user's location from their public IP address. Free IP
        # geolocation APIs are individually flaky (rate limits, outages,
        # blocking default urllib user agents), so try a few in turn and
        # only give up once all of them have failed.
        providers = (
            self._geolocate_ipapi_co,
            self._geolocate_ipwhois,
            self._geolocate_ipinfo,
        )

        last_error = None

        for provider in providers:
            try:
                return provider()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        raise ValueError(
            "Could not determine location from IP"
            + (f": {last_error}" if last_error else "")
        )

    def _ip_request(self, url):
        # A handful of free IP-geolocation providers reject requests
        # carrying urllib's default "Python-urllib/x.y" user agent, so
        # send a normal-looking one instead.
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (dripfetch)"},
        )
        with urllib.request.urlopen(
            request,
            timeout=self.TIMEOUT,
        ) as response:
            return json.load(response)

    def _geolocate_ipapi_co(self):
        data = self._ip_request("https://ipapi.co/json/")

        if data.get("error"):
            raise ValueError(
                data.get("reason", "ipapi.co lookup failed")
            )

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if latitude is None or longitude is None:
            raise ValueError("ipapi.co returned no coordinates")

        location = self._place(
            data.get("city", ""),
            data.get("country_code", ""),
        )

        return latitude, longitude, location

    def _geolocate_ipwhois(self):
        data = self._ip_request("https://ipwho.is/")

        if data.get("success") is False:
            raise ValueError(
                data.get("message", "ipwho.is lookup failed")
            )

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if latitude is None or longitude is None:
            raise ValueError("ipwho.is returned no coordinates")

        location = self._place(
            data.get("city", ""),
            data.get("country_code", ""),
        )

        return latitude, longitude, location

    def _geolocate_ipinfo(self):
        data = self._ip_request("https://ipinfo.io/json")

        coordinates = data.get("loc", "")
        parts = coordinates.split(",", 1)

        if len(parts) != 2:
            raise ValueError("ipinfo.io returned no coordinates")

        try:
            latitude = float(parts[0])
            longitude = float(parts[1])
        except ValueError as exc:
            raise ValueError("ipinfo.io returned bad coordinates") from exc

        # ipinfo.io's "country" field is already the ISO alpha-2 code.
        location = self._place(
            data.get("city", ""),
            data.get("country", ""),
        )

        return latitude, longitude, location

    def _fetch(self):
        try:
            (
                latitude,
                longitude,
                location,
            ) = self._geocode()

            params = urllib.parse.urlencode(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "daily": "weather_code,temperature_2m_max",
                    "temperature_unit": self.temperature_unit,
                    "timezone": "auto",
                    "forecast_days": self.days_count,
                }
            )

            with urllib.request.urlopen(
                (
                    "https://api.open-meteo.com/"
                    f"v1/forecast?{params}"
                ),
                timeout=self.TIMEOUT,
            ) as response:
                daily = json.load(response)["daily"]

            forecast = []

            for index, value in enumerate(
                daily["time"]
            ):
                date = datetime.fromisoformat(value)

                forecast.append(
                    {
                        "day": (
                            "Today"
                            if index == 0
                            else date.strftime("%a")
                        ),
                        "condition": self.CODES.get(
                            daily["weather_code"][index],
                            "Unknown",
                        ),
                        "temp": self._value(
                            daily[
                                "temperature_2m_max"
                            ][index]
                        ),
                    }
                )

            with self._lock:
                self.forecast = forecast
                self.location_name = location
                self.error = None
                self.loading = False
                self.last_update = (
                    time.monotonic()
                )

        except Exception as exc:
            with self._lock:
                self.error = str(exc)
                self.loading = False

    @staticmethod
    def _value(value):
        if value is None:
            return "--"

        return str(round(value))

    def update(self):
        if (
            time.monotonic() - self.last_update
            >= self.CACHE_TIME
        ):
            self._start_fetch()

    def _format(self, day):
        temp = f"{day['temp']}\u00b0{self.degree_letter}"

        return (
            f"{day['day']:<6}"
            f"{temp:>5} "
            f"{day['condition']}"
        )

    def content(self):
        with self._lock:
            forecast = list(self.forecast)
            loading = self.loading
            location = self.location_name

        if not forecast:
            text = "Fetching weather..." if loading else "Weather unavailable"
            return [[(text, self.colors.body)]]

        title = f"WEATHER / {location.upper()}"
        rows = [self._format(day) for day in forecast[: self.days_count]]

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