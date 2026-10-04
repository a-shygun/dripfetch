import contextlib

from .colors import BoxColors
from .layout import BoxLayout
from .placement import Placement
from .registry import TYPES


class BoxManager:
    TYPES = TYPES

    def __init__(
        self,
        stdscr,
        config,
        config_path,
        renderer,
        save_config,
    ):
        self.stdscr = stdscr
        self.config = config
        self.config_path = config_path
        self.save_config = save_config
        self.renderer = renderer
        self.box_config = config.get("boxes", {})
        self.box_configs = self.box_config.get("items", [])
        keyboard_layout = config.get("keyboard", {}).get("layout", "qwerty")
        self.selected = None
        self.placement = Placement(stdscr, keyboard_layout)
        self.boxes = [self._create_box(item) for item in self.box_configs]
        self.layout = BoxLayout(
            stdscr,
            self.placement,
            self.boxes,
            self.box_configs,
            self.box_config,
        )

    def _create_box(self, config):
        box_type = config.get("type", "text")
        # Fall back to TextBox if the type isn't found.
        box_class = self.TYPES.get(box_type, self.TYPES.get("text"))
        return box_class(
            self.stdscr,
            config,
            self.box_config,
            BoxColors(self.config),
            self.renderer,
        )

    def _title(self, index):
        return self.box_configs[index].get("title")

    def _save_position(self, index):
        horizontal, vertical = self.layout.relative_position(index)
        position = self.box_configs[index].setdefault("position", {})
        position["horizontal"] = horizontal
        position["vertical"] = vertical
        with contextlib.suppress(OSError):
            self.save_config(self.config, self.config_path)

    # ------------------------------------------------------------------
    # Bounds (used by the rain for collisions)
    # ------------------------------------------------------------------
    def get_box_bounds(self, index):
        return self.layout.bounds(index)

    def get_box_bounds_list(self):
        return self.layout.bounds_list()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_mouse(self, x, y):
        index = self.layout.hit_test(x, y)
        if index is not None:
            self.selected = index

    def handle_key(self, key):
        if key == 27:
            self.selected = None
            return
        if self.selected is None:
            return
        if self.layout.move(self.selected, key):
            self._save_position(self.selected)

    # ------------------------------------------------------------------
    # Frame lifecycle
    # ------------------------------------------------------------------
    def resize(self):
        self.layout.resize()

    def update(self):
        for box in self.boxes:
            box.update()
        # Some boxes (notably sysinfo) populate their content asynchronously.
        # Their final dimensions must be applied to the saved center-relative
        # position instead of retaining the temporary loading-size origin.
        self.layout.sync_dimensions()

    def draw(self):
        for index, box in enumerate(self.boxes):
            width, height = self.layout.dimensions(index)
            x, y = self.layout.positions[index]
            self.layout.border(index).draw(
                self.renderer,
                x,
                y,
                width,
                height,
                box.colors.border,
                index == self.selected,
                self._title(index),
            )
            box.draw_content(*self.layout.content_geometry(index, width, height))

    def close(self):
        for box in self.boxes:
            box.close()
