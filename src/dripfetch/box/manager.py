# import contextlib

# from .base import BaseBox, Border, BoxColors, Placement
# from .types.clock import ClockBox
# from .types.logo import LogoBox
# from .types.sysinfo import SysInfoBox
# from .types.text import TextBox
# from .types.weather import WeatherBox


# # ---------------------------------------------------------------------------
# # Box manager
# # ---------------------------------------------------------------------------
# class BoxManager:
#     TYPES = {
#         "text": TextBox,
#         "sysinfo": SysInfoBox,
#         "clock": ClockBox,
#         "logo": LogoBox,
#         "weather": WeatherBox,
#     }

#     def __init__(
#         self,
#         stdscr,
#         config,
#         config_path,
#         renderer,
#         save_config,
#     ):
#         self.stdscr = stdscr
#         self.config = config
#         self.config_path = config_path
#         self.save_config = save_config
#         self.renderer = renderer
#         self.box_config = config.get("boxes", {})
#         self.box_configs = self.box_config.get("items", [])
#         keyboard_config = config.get("keyboard", {})
#         keyboard_layout = keyboard_config.get(
#             "layout",
#             "qwerty",
#         )
#         self.boxes = []
#         self.positions = []
#         self.selected = None
#         self.placement = Placement(
#             stdscr,
#             keyboard_layout,
#         )
#         self._terminal_size = None
#         self._initialize()

#     def _initialize(self):
#         self.boxes = [self._create_box(config) for config in self.box_configs]
#         self.positions = [self._center(index) for index in range(len(self.boxes))]
#         for index in range(len(self.positions)):
#             self._clamp(index)
#         self._terminal_size = self.stdscr.getmaxyx()

#     def _create_box(self, config):
#         box_type = config.get("type", "text")
#         box_class = self.TYPES.get(
#             box_type,
#             TextBox,
#         )
#         colors = BoxColors(
#             self.config,
#             config,
#         )
#         return box_class(
#             self.stdscr,
#             config,
#             self.box_config,
#             colors,
#             self.renderer,
#         )

#     def _border(self, index):
#         config = self.box_configs[index]
#         name = config.get(
#             "border",
#             self.box_config.get(
#                 "border",
#                 "single",
#             ),
#         )
#         return Border(name)

#     def _dimensions(self, index):
#         box = self.boxes[index]
#         content_width, content_height = box.dimensions()
#         horizontal, vertical = box.padding
#         return self._border(index).dimensions(
#             content_width,
#             content_height,
#             horizontal,
#             vertical,
#         )

#     def _content_geometry(self, index, width, height):
#         x, y = self.positions[index]
#         horizontal, vertical = self.boxes[index].padding
#         content_width = width - 2 - horizontal * 2
#         content_height = height - 2 - vertical * 2
#         return (
#             x + 1 + horizontal,
#             y + 1 + vertical,
#             content_width,
#             content_height,
#         )

#     def _center(self, index):
#         width, height = self._dimensions(index)
#         return self.placement.center(
#             width,
#             height,
#             self.box_configs[index].get("position"),
#         )

#     def _clamp(self, index):
#         width, height = self._dimensions(index)
#         self.placement.clamp(
#             self.positions[index],
#             width,
#             height,
#         )

#     def resize(self):
#         size = self.stdscr.getmaxyx()
#         if size == self._terminal_size:
#             return
#         self._terminal_size = size
#         for index in range(len(self.boxes)):
#             self.positions[index] = self._center(index)
#             self._clamp(index)

#     def _relative_position(self, index):
#         width, height = self._dimensions(index)
#         return self.placement.relative(
#             self.positions[index],
#             width,
#             height,
#         )

#     def _save_position(self, index):
#         horizontal, vertical = self._relative_position(index)
#         position = self.box_configs[index].setdefault(
#             "position",
#             {},
#         )
#         position["horizontal"] = horizontal
#         position["vertical"] = vertical
#         # Only swallow genuine write failures here (disk full, permission
#         # denied, etc.) -- those are things a position save can
#         # reasonably fail on without derailing the session. ConfigError
#         # (raised by validate_config inside save_config) is also a
#         # ValueError subclass, but it means the config is actually
#         # invalid, and silently eating that made a real bug here
#         # (a stale RAIN_EFFECTS list) look like "saving does nothing"
#         # instead of surfacing the actual error.
#         with contextlib.suppress(OSError):
#             self.save_config(
#                 self.config,
#                 self.config_path,
#             )

#     def get_box_bounds(self, index):
#         if not 0 <= index < len(self.boxes):
#             return None
#         x, y = self.positions[index]
#         width, height = self._dimensions(index)
#         return (
#             x,
#             y,
#             x + width - 1,
#             y + height - 1,
#         )

#     def get_box_bounds_list(self):
#         return [self.get_box_bounds(index) for index in range(len(self.boxes))]

#     def handle_mouse(self, x, y):
#         for index in range(len(self.boxes)):
#             bounds = self.get_box_bounds(index)
#             if bounds is None:
#                 continue
#             left, top, right, bottom = bounds
#             if left <= x <= right and top <= y <= bottom:
#                 self.selected = index
#                 return

#     def handle_key(self, key):
#         # Escape exits box-moving mode.
#         if key == 27:
#             self.selected = None
#             return
#         # No selected box means we are not in moving mode.
#         if self.selected is None:
#             return
#         position = self.positions[self.selected]
#         if not self.placement.move(position, key):
#             return
#         self._clamp(self.selected)
#         self._save_position(self.selected)

#     def update(self):
#         for box in self.boxes:
#             box.update()

#     def draw(self):
#         for index, box in enumerate(self.boxes):
#             width, height = self._dimensions(index)
#             x, y = self.positions[index]
#             self._border(index).draw(
#                 self.renderer,
#                 x,
#                 y,
#                 width,
#                 height,
#                 box.colors.border,
#                 index == self.selected,
#             )
#             content = self._content_geometry(
#                 index,
#                 width,
#                 height,
#             )
#             box.draw_content(*content)

#     def close(self):
#         for box in self.boxes:
#             box.close()

import contextlib
import importlib
import inspect
import pkgutil

from .base import BaseBox, Border, BoxColors, Placement


def get_box_types():
    """Return the names of the box classes discovered by BoxManager."""
    return set(BoxManager.TYPES)


def validate_box_config(config):
    """Validate the boxes section, including each discovered box type."""
    # Reuse config's primitive validators while keeping all box-specific
    # rules and type discovery with the box manager.
    from ..app import config as config_validation

    mapping = config_validation._mapping
    enum = config_validation._enum
    color = config_validation._color
    integer = config_validation._integer
    string = config_validation._string
    error = config_validation._error

    boxes = mapping(config.get("boxes", {}), "boxes")
    border_types = set(Border.TYPES)
    if "border" in boxes:
        enum(boxes["border"], "boxes.border", border_types)
    for key in ("border_color", "text_color", "accent_color"):
        if key in boxes:
            color(boxes[key], f"boxes.{key}")
    if "padding" in boxes:
        padding = mapping(boxes["padding"], "boxes.padding")
        for key in ("horizontal", "vertical"):
            if key not in padding:
                continue
            value = integer(padding[key], f"boxes.padding.{key}")
            if value < 0:
                error(f"boxes.padding.{key}", "must be greater than or equal to 0")

    items = boxes.get("items", [])
    if not isinstance(items, list):
        error("boxes.items", "must be a list")
    for index, item in enumerate(items):
        path = f"boxes.items[{index}]"
        item = mapping(item, path)
        box_type = item.get("type", "text")
        enum(box_type, f"{path}.type", BoxManager.TYPES)
        if "border" in item:
            enum(item["border"], f"{path}.border", border_types)
        if "title" in item:
            string(item["title"], f"{path}.title")
        if "position" in item:
            position = mapping(item["position"], f"{path}.position")
            for key in ("horizontal", "vertical"):
                if key in position:
                    integer(position[key], f"{path}.position.{key}")
        box_class = BoxManager.TYPES.get(box_type)
        if box_class is not None and hasattr(box_class, "validate_config"):
            box_class.validate_config(item, path)


# ---------------------------------------------------------------------------
# Auto-discovery: scan box/types/ and collect every BaseBox subclass.
# Adding a new box type is now just: drop a .py file in box/types/.
# No registration needed here or in config.py.
# ---------------------------------------------------------------------------
def _discover_types():
    """Return a {type_name: box_class} dict built from box/types/*.py.

    The type name is the module's stem (e.g. ``clock`` from ``clock.py``).
    Each module is expected to contain exactly one non-abstract BaseBox
    subclass; if a module contains several, the first one found is used.
    Modules that contain no such class are silently skipped so that
    __init__.py or helper modules sitting in the same directory don't break
    discovery.
    """
    types: dict[str, type[BaseBox]] = {}

    # Resolve the package path for box.types relative to this file so
    # discovery works whether the package is installed or run in-tree.
    from . import types as _types_pkg  # box/types/__init__.py

    for module_info in pkgutil.iter_modules(_types_pkg.__path__):
        if module_info.name.startswith("_"):
            continue  # skip __init__ and private helpers
        module = importlib.import_module(
            f".types.{module_info.name}",
            package=__package__,
        )
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseBox)
                and obj is not BaseBox
                and obj.__module__ == module.__name__
            ):
                types[module_info.name] = obj
                break  # one class per module is the convention

    return types


class BoxManager:
    # Populated once at class-definition time so the scan runs only on
    # first import, not on every instantiation.
    TYPES: dict[str, type[BaseBox]] = _discover_types()

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
        keyboard_config = config.get("keyboard", {})
        keyboard_layout = keyboard_config.get(
            "layout",
            "qwerty",
        )
        self.boxes = []
        self.positions = []
        self.selected = None
        self.placement = Placement(
            stdscr,
            keyboard_layout,
        )
        self._terminal_size = None
        self._box_dimensions = []
        self._initialize()

    def _initialize(self):
        self.boxes = [self._create_box(config) for config in self.box_configs]
        self._box_dimensions = [
            self._dimensions(index)
            for index in range(len(self.boxes))
        ]
        self.positions = [self._center(index) for index in range(len(self.boxes))]
        for index in range(len(self.positions)):
            self._clamp(index)
        self._terminal_size = self.stdscr.getmaxyx()

    def _create_box(self, config):
        box_type = config.get("type", "text")
        # Fall back to TextBox if the type isn't found -- same behaviour as
        # before, but now TextBox is fetched from the discovered map too.
        fallback = self.TYPES.get("text")
        box_class = self.TYPES.get(box_type, fallback)
        colors = BoxColors(self.config)
        return box_class(
            self.stdscr,
            config,
            self.box_config,
            colors,
            self.renderer,
        )

    def _border(self, index):
        config = self.box_configs[index]
        name = config.get(
            "border",
            self.box_config.get(
                "border",
                "single",
            ),
        )
        return Border(name)

    def _title(self, index):
        return self.box_configs[index].get("title")

    def _dimensions(self, index):
        box = self.boxes[index]
        content_width, content_height = box.dimensions()
        horizontal, vertical = box.padding
        return self._border(index).dimensions(
            content_width,
            content_height,
            horizontal,
            vertical,
        )

    def _content_geometry(self, index, width, height):
        x, y = self.positions[index]
        horizontal, vertical = self.boxes[index].padding
        content_width = width - 2 - horizontal * 2
        content_height = height - 2 - vertical * 2
        return (
            x + 1 + horizontal,
            y + 1 + vertical,
            content_width,
            content_height,
        )

    def _center(self, index):
        width, height = self._dimensions(index)
        return self.placement.center(
            width,
            height,
            self.box_configs[index].get("position"),
        )

    def _clamp(self, index):
        width, height = self._dimensions(index)
        self.placement.clamp(
            self.positions[index],
            width,
            height,
        )

    def resize(self):
        size = self.stdscr.getmaxyx()
        if size == self._terminal_size:
            return
        self._terminal_size = size
        for index in range(len(self.boxes)):
            self._box_dimensions[index] = self._dimensions(index)
            self.positions[index] = self._center(index)
            self._clamp(index)

    def _sync_box_dimensions(self):
        """Reapply center-relative saved positions when a box changes size."""
        for index in range(len(self.boxes)):
            dimensions = self._dimensions(index)
            if dimensions == self._box_dimensions[index]:
                continue
            self._box_dimensions[index] = dimensions
            self.positions[index] = self._center(index)
            self._clamp(index)

    def _relative_position(self, index):
        width, height = self._dimensions(index)
        return self.placement.relative(
            self.positions[index],
            width,
            height,
        )

    def _save_position(self, index):
        horizontal, vertical = self._relative_position(index)
        position = self.box_configs[index].setdefault(
            "position",
            {},
        )
        position["horizontal"] = horizontal
        position["vertical"] = vertical
        with contextlib.suppress(OSError):
            self.save_config(
                self.config,
                self.config_path,
            )

    def get_box_bounds(self, index):
        if not 0 <= index < len(self.boxes):
            return None
        x, y = self.positions[index]
        width, height = self._dimensions(index)
        return (
            x,
            y,
            x + width - 1,
            y + height - 1,
        )

    def get_box_bounds_list(self):
        return [self.get_box_bounds(index) for index in range(len(self.boxes))]

    def handle_mouse(self, x, y):
        for index in range(len(self.boxes)):
            bounds = self.get_box_bounds(index)
            if bounds is None:
                continue
            left, top, right, bottom = bounds
            if left <= x <= right and top <= y <= bottom:
                self.selected = index
                return

    def handle_key(self, key):
        if key == 27:
            self.selected = None
            return
        if self.selected is None:
            return
        position = self.positions[self.selected]
        if not self.placement.move(position, key):
            return
        self._clamp(self.selected)
        self._save_position(self.selected)

    def update(self):
        for box in self.boxes:
            box.update()
        # Some boxes (notably sysinfo) populate their content asynchronously.
        # Their final dimensions must be applied to the saved center-relative
        # position instead of retaining the temporary loading-size origin.
        self._sync_box_dimensions()

    def draw(self):
        for index, box in enumerate(self.boxes):
            width, height = self._dimensions(index)
            x, y = self.positions[index]
            self._border(index).draw(
                self.renderer,
                x,
                y,
                width,
                height,
                box.colors.border,
                index == self.selected,
                self._title(index),
            )
            content = self._content_geometry(
                index,
                width,
                height,
            )
            box.draw_content(*content)

    def close(self):
        for box in self.boxes:
            box.close()
