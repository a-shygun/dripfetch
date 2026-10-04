from .constants import ACCEL_FLOOR, ACCEL_RATE, BOX_PADDING


def find_collision(x, old_y, new_y, bounds, enabled):
    if not enabled:
        return None

    for (
        left,
        top,
        right,
        bottom,
    ) in bounds:
        if (
            old_y < top <= new_y
            and left <= x <= right
        ):
            targets = (
                left - BOX_PADDING,
                right + BOX_PADDING,
            )

            target = min(
                targets,
                key=lambda value: abs(x - value),
            )

            return target, top

    return None


def inside_box(x, y, bounds):
    return any(
        left <= x <= right
        and top <= y <= bottom
        for (
            left,
            top,
            right,
            bottom,
        ) in bounds
    )


def current_speed(drop, now, fx_acceleration):
    if not fx_acceleration:
        return drop.speed

    age = max(0.0, now - drop.spawned_at)
    factor = max(
        ACCEL_FLOOR,
        1 - age * ACCEL_RATE,
    )

    return max(5.0, drop.base_speed * factor)


def move_horizontal(drop, width):
    target = drop.redirect_target

    if target is None:
        return

    if drop.x == target:
        drop.redirect_target = None
        return

    direction = (
        1 if target > drop.x else -1
    )

    drop.x += direction

    # A box can touch the terminal edge. Let the drop finish its
    # deflection beyond that edge instead of stopping at the last
    # visible column and colliding with the same side forever.
    if not 0 <= drop.x < width:
        drop.active = False
        drop.redirect_target = None
        return

    if drop.character in ("│", "|"):
        drop.path.append(
            (
                drop.x,
                drop.head_y,
                "─",
            )
        )

        if drop.x == target:
            drop.path[-1] = (
                drop.x,
                drop.head_y,
                "┐"
                if direction > 0
                else "┌",
            )

            drop.redirect_target = None

        return

    drop.path.append(
        (
            drop.x,
            drop.head_y,
            drop.character,
        )
    )

    if drop.x == target:
        drop.redirect_target = None


def move_down(drop, bounds, collision_enabled):
    old_x = drop.x
    old_y = drop.head_y

    hit = find_collision(
        old_x,
        old_y,
        old_y + 1,
        bounds,
        collision_enabled,
    )

    if hit:
        target, top = hit

        drop.head_y = top - 1
        drop.redirect_target = target

        if drop.character in ("│", "|"):
            corner = (
                "└"
                if target > old_x
                else "┘"
            )

            if drop.path:
                drop.path[-1] = (
                    old_x,
                    drop.head_y,
                    corner,
                )
            else:
                drop.path.append(
                    (
                        old_x,
                        drop.head_y,
                        corner,
                    )
                )

        return

    drop.head_y += 1

    drop.path.append(
        (
            drop.x,
            drop.head_y,
            drop.character,
        )
    )


def update_drop(drop, now, bounds, width, height, collision_enabled, fx_acceleration):
    if not drop.active:
        return

    speed = current_speed(drop, now, fx_acceleration)

    interval = max(
        1.0,
        float(speed),
    ) / 1000

    elapsed = now - drop.last_move

    if elapsed < interval:
        return

    steps = min(
        max(
            1,
            int(elapsed / interval),
        ),
        8,
    )

    for _ in range(steps):
        if drop.redirect_target is None:
            move_down(
                drop,
                bounds,
                collision_enabled,
            )
        else:
            move_horizontal(
                drop,
                width,
            )

        if (
            drop.head_y - drop.length
            >= height
        ):
            drop.active = False
            break

    drop.last_move = now