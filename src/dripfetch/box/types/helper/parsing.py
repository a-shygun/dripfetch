"""Forgiving readers for optional box settings (fall back instead of raising)."""

from ....app.terminal import parse_color


def clamp_int(value, minimum, maximum=None, default=None):
    """int(value) limited to [minimum, maximum]; ``default`` (or minimum) on bad input."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return minimum if default is None else default
    value = max(minimum, value)
    return value if maximum is None else min(maximum, value)


def clamp_float(value, minimum, default):
    """float(value) with a lower bound; ``default`` on bad input."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


def color_or_default(value, default):
    """Parse a #RRGGBB[AA] string, or return ``default`` if absent/invalid."""
    if not value:
        return default
    try:
        return parse_color(value)
    except Exception:  # noqa: BLE001
        return default
