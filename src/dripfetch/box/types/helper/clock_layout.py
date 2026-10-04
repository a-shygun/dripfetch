"""Turns the current time into glyph rows for the clock box."""

import time
from dataclasses import dataclass
from typing import NamedTuple

from .clock_digits import DIGITS


@dataclass(frozen=True, slots=True)
class ClockOptions:
    style: str = "single"
    size: str = "medium"
    clock_24h: bool = True
    show_seconds: bool = True
    show_am_pm: bool = True
    blink_colon: bool = False
    show_date: bool = False

    @classmethod
    def from_config(cls, config):
        return cls(
            style=config.get("clock_style", "single"),
            size=config.get("clock_size", "medium"),
            clock_24h=config.get("clock_24h", True),
            show_seconds=config.get("show_seconds", True),
            show_am_pm=config.get("show_am_pm", True),
            blink_colon=config.get("blink_colon", False),
            show_date=config.get("show_date", False),
        )


class ClockGeometry(NamedTuple):
    text: str
    patterns: list
    spacing: int
    width: int
    height: int
    date: str

    @property
    def content_width(self):
        return max(self.width, len(self.date))

    @property
    def content_height(self):
        return self.height + bool(self.date) * 2


def _blank(pattern):
    return [" " * len(line) for line in pattern]


def time_text(now, options):
    hour = "%H" if options.clock_24h else "%I"
    seconds = ":%S" if options.show_seconds else ""
    text = time.strftime(f"{hour}:%M{seconds}", now)
    if not options.clock_24h and options.show_am_pm:
        text = f"{text} {time.strftime('%p', now)}"
    return text


def glyph_patterns(text, now, options):
    digits = DIGITS[options.style][options.size]
    show_colon = not options.blink_colon or now.tm_sec % 2 == 0
    blank_digit = _blank(digits["0"])
    return [
        _blank(digits[char])
        if char == ":" and not show_colon
        else digits.get(char, blank_digit)
        for char in text
    ]


def build_geometry(now, options):
    text = time_text(now, options)
    patterns = glyph_patterns(text, now, options)
    spacing = 2 if options.size == "big" else 1
    width = sum(len(pattern[0]) for pattern in patterns)
    width += (len(patterns) - 1) * spacing
    height = len(patterns[0])
    date = time.strftime("%A, %b %d %Y", now) if options.show_date else ""
    return ClockGeometry(text, patterns, spacing, width, height, date)
