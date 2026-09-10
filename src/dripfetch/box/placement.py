class Placement:
    MOVEMENT = {
        ord("w"): (0, -1),
        ord("a"): (-1, 0),
        ord("s"): (0, 1),
        ord("d"): (1, 0),
    }

    def __init__(self, stdscr):
        self.stdscr = stdscr

    def center(self, width, height, offset=None):
        terminal_height, terminal_width = self.stdscr.getmaxyx()
        offset = offset or {}
        return [
            (terminal_width - width) // 2 + offset.get("horizontal", 0),
            (terminal_height - height) // 2 + offset.get("vertical", 0),
        ]

    def clamp(self, position, width, height):
        terminal_height, terminal_width = self.stdscr.getmaxyx()
        position[0] = max(0, min(position[0], max(0, terminal_width - width)))
        position[1] = max(0, min(position[1], max(0, terminal_height - height)))
        return position

    def move(self, position, key):
        if key not in self.MOVEMENT:
            return False

        dx, dy = self.MOVEMENT[key]
        position[0] += dx
        position[1] += dy
        return True

    def relative(self, position, width, height):
        terminal_height, terminal_width = self.stdscr.getmaxyx()
        return (
            position[0] - (terminal_width - width) // 2,
            position[1] - (terminal_height - height) // 2,
        )
