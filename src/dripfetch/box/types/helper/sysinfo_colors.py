"""Coloring of the sysinfo tree: box-drawing glyphs vs. text vs. titles."""

LINE_CHARS = "┌─│├└┐┘┤┬┴┼"
TITLES = {
    "SYSTEM",
    "DISPLAY",
    "HARDWARE",
    "DISK",
    "CONNECTIVITY",
}


def _title(line):
    for title in TITLES:
        if line.endswith(title):
            return title

    return None


def color_text(text, line_color, text_color):
    """Split ``text`` into runs of (substring, color), grouping equal colors."""
    if not text:
        return []

    segments = []
    start = 0
    current = line_color if text[0] in LINE_CHARS else text_color

    for index in range(1, len(text)):
        color = line_color if text[index] in LINE_CHARS else text_color

        if color == current:
            continue

        segments.append((text[start:index], current))
        start = index
        current = color

    segments.append((text[start:], current))

    return segments


def color_line(line, colors):
    title = _title(line)

    if title:
        prefix = line[: -len(title)]
        segments = color_text(prefix, colors.line, colors.text)
        segments.append((title, colors.title))
        return segments

    return color_text(line, colors.line, colors.text)
