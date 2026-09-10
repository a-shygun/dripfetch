from .collision import collision


def move_horizontal(drop):
    target = drop.redirect_target
    if target is None:
        return
    direction = 1 if target > drop.x else -1
    drop.x += direction
    drop.path.append((drop.x, drop.head_y, "─"))
    if drop.x == target:
        drop.path[-1] = (
            drop.x,
            drop.head_y,
            "┐" if direction > 0 else "┌",
        )
        drop.redirect_target = None


def move_down(drop, bounds, collision_enabled, width, character):
    old_x = drop.x
    old_y = drop.head_y
    hit = collision(
        old_x,
        old_y,
        old_y + 1,
        bounds,
        collision_enabled,
        width,
    )
    if hit:
        target, top = hit
        drop.head_y = top - 1
        drop.redirect_target = target
        corner = "└" if target > old_x else "┘"
        if drop.path:
            drop.path[-1] = (
                old_x,
                drop.head_y,
                corner,
            )
        else:
            drop.path.append((old_x, drop.head_y, corner))
        return
    drop.head_y += 1
    drop.path.append((drop.x, drop.head_y, character))
