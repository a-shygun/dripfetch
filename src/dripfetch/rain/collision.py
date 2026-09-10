BOX_PADDING = 2


def collision(x, old_y, new_y, bounds, enabled, width):
    if not enabled:
        return None
    for left, top, right, bottom in bounds:
        if old_y < top <= new_y and left <= x <= right:
            targets = (
                max(0, left - BOX_PADDING),
                min(width - 1, right + BOX_PADDING),
            )
            return min(
                targets,
                key=lambda target: abs(x - target),
            ), top
    return None


def inside_box(x, y, bounds):
    return any(
        left <= x <= right and top <= y <= bottom for left, top, right, bottom in bounds
    )
