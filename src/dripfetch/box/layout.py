from .border import Border


class BoxLayout:
    """Owns where each box sits on screen and how big it is.

    Positions are stored as absolute terminal cells but are derived from
    the center-relative offsets saved in the config, so they are recomputed
    whenever the terminal or a box changes size.
    """

    def __init__(self, stdscr, placement, boxes, box_configs, box_defaults):
        self.stdscr = stdscr
        self.placement = placement
        self.boxes = boxes
        self.box_configs = box_configs
        self.box_defaults = box_defaults
        self.positions = []
        self._terminal_size = None
        self._box_dimensions = []
        self._initialize()

    def _initialize(self):
        count = len(self.boxes)
        self._box_dimensions = [self.dimensions(index) for index in range(count)]
        self.positions = [self._center(index) for index in range(count)]
        for index in range(count):
            self._clamp(index)
        self._terminal_size = self.stdscr.getmaxyx()

    # ------------------------------------------------------------------
    # Per-box geometry
    # ------------------------------------------------------------------
    def border(self, index):
        name = self.box_configs[index].get(
            "border",
            self.box_defaults.get("border", "single"),
        )
        return Border(name)

    def dimensions(self, index):
        box = self.boxes[index]
        content_width, content_height = box.dimensions()
        horizontal, vertical = box.padding
        return self.border(index).dimensions(
            content_width,
            content_height,
            horizontal,
            vertical,
        )

    def content_geometry(self, index, width, height):
        x, y = self.positions[index]
        horizontal, vertical = self.boxes[index].padding
        return (
            x + 1 + horizontal,
            y + 1 + vertical,
            width - 2 - horizontal * 2,
            height - 2 - vertical * 2,
        )

    def _center(self, index):
        width, height = self.dimensions(index)
        return self.placement.center(
            width,
            height,
            self.box_configs[index].get("position"),
        )

    def _clamp(self, index):
        width, height = self.dimensions(index)
        self.placement.clamp(self.positions[index], width, height)

    def relative_position(self, index):
        width, height = self.dimensions(index)
        return self.placement.relative(self.positions[index], width, height)

    # ------------------------------------------------------------------
    # Keeping positions in sync
    # ------------------------------------------------------------------
    def resize(self):
        size = self.stdscr.getmaxyx()
        if size == self._terminal_size:
            return
        self._terminal_size = size
        for index in range(len(self.boxes)):
            self._box_dimensions[index] = self.dimensions(index)
            self.positions[index] = self._center(index)
            self._clamp(index)

    def sync_dimensions(self):
        """Reapply center-relative saved positions when a box changes size."""
        for index in range(len(self.boxes)):
            dimensions = self.dimensions(index)
            if dimensions == self._box_dimensions[index]:
                continue
            self._box_dimensions[index] = dimensions
            self.positions[index] = self._center(index)
            self._clamp(index)

    def move(self, index, key):
        """Move a box for a movement key. Returns True if it moved."""
        if not self.placement.move(self.positions[index], key):
            return False
        self._clamp(index)
        return True

    # ------------------------------------------------------------------
    # Hit testing / bounds
    # ------------------------------------------------------------------
    def bounds(self, index):
        if not 0 <= index < len(self.boxes):
            return None
        x, y = self.positions[index]
        width, height = self.dimensions(index)
        return (
            x,
            y,
            x + width - 1,
            y + height - 1,
        )

    def bounds_list(self):
        return [self.bounds(index) for index in range(len(self.boxes))]

    def hit_test(self, x, y):
        """Return the index of the first box containing (x, y), else None."""
        for index in range(len(self.boxes)):
            bounds = self.bounds(index)
            if bounds is None:
                continue
            left, top, right, bottom = bounds
            if left <= x <= right and top <= y <= bottom:
                return index
        return None
