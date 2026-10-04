import importlib
import inspect
import pkgutil

from .base import BaseBox


# ---------------------------------------------------------------------------
# Auto-discovery: scan box/types/ and collect every BaseBox subclass.
# Adding a new box type is just: drop a .py file in box/types/.
# No registration needed here or in config.py.
# ---------------------------------------------------------------------------
def discover_types():
    """Return a {type_name: box_class} dict built from box/types/*.py.

    The type name is the module's stem (e.g. ``clock`` from ``clock.py``).
    Each module is expected to contain exactly one non-abstract BaseBox
    subclass; if a module contains several, the first one found is used.
    Modules that contain no such class are silently skipped, and
    sub-packages (such as ``types/helper/``) are never scanned, so support
    code can live next to the box types without breaking discovery.
    """
    types: dict[str, type[BaseBox]] = {}

    # Resolve the package path for box.types relative to this file so
    # discovery works whether the package is installed or run in-tree.
    from . import types as _types_pkg  # box/types/__init__.py

    for module_info in pkgutil.iter_modules(_types_pkg.__path__):
        if module_info.ispkg or module_info.name.startswith("_"):
            continue  # skip helper/ (a package) and private modules
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


# Populated once at import time so the scan runs only on first import.
TYPES: dict[str, type[BaseBox]] = discover_types()


def get_box_types():
    """Return the names of the discovered box types."""
    return set(TYPES)
