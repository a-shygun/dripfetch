"""Turning a city name, coordinates, or the caller's IP into a location."""

from .web import build_url, get_json

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# A handful of free IP-geolocation providers reject requests carrying
# urllib's default "Python-urllib/x.y" user agent, so send a normal-looking one.
_IP_HEADERS = {"User-Agent": "Mozilla/5.0 (dripfetch)"}

# A few country codes people expect to see written a bit differently
# than the bare ISO 3166-1 alpha-2 code an API hands back.
_COUNTRY_OVERRIDES = {
    "US": "USA",
    "GB": "UK",
}


def short_country(code):
    code = (code or "").strip().upper()
    if not code:
        return ""
    return _COUNTRY_OVERRIDES.get(code, code)


def place(city, country_code):
    city = (city or "").strip()
    country = short_country(country_code)
    return f"{city}, {country}".strip(", ") or "Unknown"


def geocode_location(name, timeout):
    url = build_url(
        GEOCODING_URL,
        {"name": name, "count": 1, "language": "en", "format": "json"},
    )
    results = get_json(url, timeout).get("results", [])

    if not results:
        raise ValueError(f"Location not found: {name}")

    result = results[0]
    return (
        result["latitude"],
        result["longitude"],
        place(result.get("name", name), result.get("country_code", "")),
    )


# ---------------------------------------------------------------------------
# IP-based fallback. Free IP geolocation APIs are individually flaky (rate
# limits, outages, blocking), so try a few in turn and only give up once all
# of them have failed.
# ---------------------------------------------------------------------------
def _from_latlon_fields(data, source):
    """Shared result shape of ipapi.co and ipwho.is."""
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:
        raise ValueError(f"{source} returned no coordinates")

    return latitude, longitude, place(data.get("city", ""), data.get("country_code", ""))


def _ipapi_co(timeout):
    data = get_json("https://ipapi.co/json/", timeout, _IP_HEADERS)

    if data.get("error"):
        raise ValueError(data.get("reason", "ipapi.co lookup failed"))

    return _from_latlon_fields(data, "ipapi.co")


def _ipwhois(timeout):
    data = get_json("https://ipwho.is/", timeout, _IP_HEADERS)

    if data.get("success") is False:
        raise ValueError(data.get("message", "ipwho.is lookup failed"))

    return _from_latlon_fields(data, "ipwho.is")


def _ipinfo(timeout):
    data = get_json("https://ipinfo.io/json", timeout, _IP_HEADERS)

    parts = data.get("loc", "").split(",", 1)

    if len(parts) != 2:
        raise ValueError("ipinfo.io returned no coordinates")

    try:
        latitude = float(parts[0])
        longitude = float(parts[1])
    except ValueError as exc:
        raise ValueError("ipinfo.io returned bad coordinates") from exc

    # ipinfo.io's "country" field is already the ISO alpha-2 code.
    return latitude, longitude, place(data.get("city", ""), data.get("country", ""))


def geolocate_by_ip(timeout):
    last_error = None

    for provider in (_ipapi_co, _ipwhois, _ipinfo):
        try:
            return provider(timeout)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise ValueError(
        "Could not determine location from IP"
        + (f": {last_error}" if last_error else "")
    )


def resolve_location(latitude, longitude, location, timeout):
    """Return (latitude, longitude, display_name) from whatever was configured."""
    if latitude is not None and longitude is not None:
        return float(latitude), float(longitude), location

    if location:
        return geocode_location(location, timeout)

    return geolocate_by_ip(timeout)
