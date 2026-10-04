"""Braille dot-graph rendering for the net box.

Each character cell is a 2 (columns) x 4 (rows) grid of dots. Standard
braille dot -> bit mapping, row 0 = top of the cell, row 3 = bottom,
col 0 = left dot column, col 1 = right dot column.
"""

BRAILLE_BASE = 0x2800
DOT_BITS = {
    0: (0x01, 0x08),
    1: (0x02, 0x10),
    2: (0x04, 0x20),
    3: (0x40, 0x80),
}


def column_cells(value, max_value, rows, mirrored):
    """Dot fill for one sample column, as ``rows`` cells of 4 booleans."""
    total_dots = rows * 4
    if max_value <= 0:
        filled = 0
    else:
        ratio = max(0.0, min(1.0, value / max_value))
        filled = round(ratio * total_dots)

    cells = [None] * rows
    remaining = filled
    row_order = range(rows) if mirrored else range(rows - 1, -1, -1)

    for r in row_order:
        n = min(4, remaining)
        remaining -= n
        cell = [False, False, False, False]
        if mirrored:
            # Baseline is at the top of this section; fill downward
            # from the top of each cell as the value grows.
            for k in range(n):
                cell[k] = True
        else:
            # Baseline is at the bottom of this section; fill upward
            # from the bottom of each cell as the value grows.
            for k in range(4 - n, 4):
                cell[k] = True
        cells[r] = cell

    return cells


def build_grid(history, rows, width, max_value, mirrored):
    """Render ``history`` as ``rows`` strings of ``width`` braille characters."""
    if rows <= 0 or width <= 0:
        return []

    samples = list(history)[-width * 2:]
    if len(samples) < width * 2:
        samples = [0] * (width * 2 - len(samples)) + samples

    row_chars = [[] for _ in range(rows)]

    for column in range(width):
        left_cells = column_cells(samples[column * 2], max_value, rows, mirrored)
        right_cells = column_cells(samples[column * 2 + 1], max_value, rows, mirrored)

        for r in range(rows):
            bits = 0
            for k in range(4):
                if left_cells[r][k]:
                    bits |= DOT_BITS[k][0]
                if right_cells[r][k]:
                    bits |= DOT_BITS[k][1]
            row_chars[r].append(chr(BRAILLE_BASE + bits))

    return ["".join(chars) for chars in row_chars]
