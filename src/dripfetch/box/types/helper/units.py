"""Human-readable number formatting."""

_RATE_UNITS = ("B/s", "K/s", "M/s", "G/s", "T/s")
_BYTE_UNITS = ("B", "KiB", "MiB", "GiB", "TiB")


def human_rate(value):
    # Kept deliberately compact (<=6 chars) so the label gutter can
    # stay narrow: no decimal once the number reaches 3 digits, and
    # single-letter unit prefixes (K/M/G/T) instead of KB/MB/etc.
    for unit in _RATE_UNITS:
        if value < 1024 or unit == _RATE_UNITS[-1]:
            if unit == "B/s" or value >= 100:
                return f"{value:.0f}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.0f}{_RATE_UNITS[-1]}"


def format_bytes(value):
    value = float(value)
    for unit in _BYTE_UNITS:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} PiB"
