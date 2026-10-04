"""Fetching and formatting the Open-Meteo daily forecast."""

from datetime import datetime

from .web import build_url, get_json

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

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


def _temperature(value):
    if value is None:
        return "--"
    return str(round(value))


def fetch_forecast(latitude, longitude, temperature_unit, days, timeout):
    """Return one {"day", "condition", "temp"} dict per forecast day."""
    url = build_url(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max",
            "temperature_unit": temperature_unit,
            "timezone": "auto",
            "forecast_days": days,
        },
    )
    daily = get_json(url, timeout)["daily"]

    forecast = []
    for index, value in enumerate(daily["time"]):
        date = datetime.fromisoformat(value)
        forecast.append(
            {
                "day": "Today" if index == 0 else date.strftime("%a"),
                "condition": CODES.get(daily["weather_code"][index], "Unknown"),
                "temp": _temperature(daily["temperature_2m_max"][index]),
            }
        )
    return forecast


def format_row(day, degree_letter):
    temp = f"{day['temp']}\u00b0{degree_letter}"
    return f"{day['day']:<6}{temp:>5} {day['condition']}"
