"""Color markers ($1, $2, ...) inside ASCII logo files."""

import re

_MARKER = re.compile(r"(\$\d+)")


def parse_line(line, palette, color):
    """Split one logo line into (text, color) segments.

    Returns the segments and the color in effect at the end of the line,
    since a marker keeps applying until the next one (even across lines).
    """
    segments = []

    for part in _MARKER.split(line):
        if not part:
            continue

        if part.startswith("$"):
            index = int(part[1:]) - 1
            color = palette[index % len(palette)]
            continue

        segments.append((part, color))

    return segments, color


def parse_logo(lines, palette, initial_color):
    content = []
    color = initial_color

    for line in lines:
        segments, color = parse_line(line, palette, color)
        content.append(segments)

    return content
