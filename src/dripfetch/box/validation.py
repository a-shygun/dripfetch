from .border import Border
from .registry import TYPES


def validate_box_config(config):
    """Validate the boxes section, including each discovered box type."""
    # Reuse config's primitive validators while keeping all box-specific
    # rules and type discovery inside the box package. Imported lazily
    # because app.config imports this module from inside validate_config.
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
        enum(box_type, f"{path}.type", TYPES)
        if "border" in item:
            enum(item["border"], f"{path}.border", border_types)
        if "title" in item:
            string(item["title"], f"{path}.title")
        if "position" in item:
            position = mapping(item["position"], f"{path}.position")
            for key in ("horizontal", "vertical"):
                if key in position:
                    integer(position[key], f"{path}.position.{key}")
        box_class = TYPES.get(box_type)
        if box_class is not None and hasattr(box_class, "validate_config"):
            box_class.validate_config(item, path)
