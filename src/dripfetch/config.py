import os
import re
import tempfile
from importlib.resources import files
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

CONFIG_DIR = Path.home() / ".config" / "dripfetch"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
BOX_TYPES = {"text", "clock", "sysinfo", "logo", "weather"}
BORDER_TYPES = {"single", "double"}
CLOCK_STYLES = {"single", "double"}
CLOCK_SIZES = {"medium", "big"}
DEFAULT_BACKGROUND = "#000000FF"


class ConfigError(ValueError):
    pass


def _yaml():
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def _error(path, message):
    raise ConfigError(f"{path}: {message}")


def _mapping(value, path):
    if not isinstance(value, dict):
        _error(path, "must be a mapping")
    return value


def _string(value, path):
    if not isinstance(value, str):
        _error(path, "must be a string")
    return value


def _bool(value, path):
    if not isinstance(value, bool):
        _error(path, "must be true or false")
    return value


def _number(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _error(path, "must be a number")
    return value


def _integer(value, path):
    if isinstance(value, bool) or not isinstance(value, int):
        _error(path, "must be an integer")
    return value


def _color(value, path):
    _string(value, path)
    if not COLOR_RE.fullmatch(value):
        _error(path, "must be #RRGGBB or #RRGGBBAA")


def _enum(value, path, choices):
    _string(value, path)
    if value not in choices:
        _error(path, f"must be one of: {', '.join(sorted(choices))}")


def _weighted_list(value, path, value_type):
    if not isinstance(value, list) or not value:
        _error(path, "must be a non-empty list")
    total = 0
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            _error(item_path, "must contain exactly two values")
        weight, item_value = item
        _number(weight, f"{item_path}[0]")
        if weight <= 0:
            _error(f"{item_path}[0]", "must be greater than 0")
        total += weight
        if value_type == "color":
            _color(item_value, f"{item_path}[1]")
        elif value_type == "integer":
            _integer(item_value, f"{item_path}[1]")
        else:
            _number(item_value, f"{item_path}[1]")
    if abs(total - 1) > 0.001:
        _error(path, "weights must sum to 1")


def _position(value, path):
    value = _mapping(value, path)
    for key in ("horizontal", "vertical"):
        if key in value:
            _integer(value[key], f"{path}.{key}")


def _validate_text(item, path):
    if "text" in item:
        _string(item["text"], f"{path}.text")


def _validate_clock(item, path):
    for key, choices in (
        ("clock_style", CLOCK_STYLES),
        ("clock_size", CLOCK_SIZES),
    ):
        if key in item:
            _enum(item[key], f"{path}.{key}", choices)
    for key in (
        "clock_24h",
        "show_seconds",
        "show_am_pm",
        "blink_colon",
        "show_date",
    ):
        if key in item:
            _bool(item[key], f"{path}.{key}")


def _validate_sysinfo(item, path):
    if "colors" not in item:
        return
    colors = _mapping(item["colors"], f"{path}.colors")
    for key in ("text", "title", "line"):
        if key in colors:
            _color(colors[key], f"{path}.colors.{key}")


def _validate_logo(item, path):
    if "logo" in item:
        logo = _string(item["logo"], f"{path}.logo")
        if not logo:
            _error(f"{path}.logo", "must not be empty")
    if "colors" in item:
        colors = item["colors"]
        if not isinstance(colors, list) or not colors:
            _error(f"{path}.colors", "must be a non-empty list")
        for index, color in enumerate(colors):
            _color(color, f"{path}.colors[{index}]")


def _validate_box(item, index):
    path = f"boxes.items[{index}]"
    item = _mapping(item, path)
    box_type = item.get("type", "text")
    _enum(box_type, f"{path}.type", BOX_TYPES)
    if "border" in item:
        _enum(item["border"], f"{path}.border", BORDER_TYPES)
    if "position" in item:
        _position(item["position"], f"{path}.position")
    validators = {
        "text": _validate_text,
        "clock": _validate_clock,
        "sysinfo": _validate_sysinfo,
        "logo": _validate_logo,
        "weather": _validate_weather,
    }
    validators[box_type](item, path)


def validate_config(config):
    config = _mapping(config, "config")
    if "background" in config:
        _color(config["background"], "background")

    rain = _mapping(config.get("rain", {}), "rain")
    if "collision" in rain:
        _bool(rain["collision"], "rain.collision")

    if "intensity" in rain:
        intensity = _integer(rain["intensity"], "rain.intensity")
        if intensity < 0:
            _error(
                "rain.intensity",
                "must be greater than or equal to 0",
            )

    if "character" in rain:
        character = _string(
            rain["character"],
            "rain.character",
        )
        if not character:
            _error(
                "rain.character",
                "must not be empty",
            )

    for key, value_type in (
        ("colors", "color"),
        ("speeds", "integer"),
        ("lengths", "integer"),
    ):
        if key in rain:
            _weighted_list(
                rain[key],
                f"rain.{key}",
                value_type,
            )

    boxes = _mapping(
        config.get("boxes", {}),
        "boxes",
    )

    if "border" in boxes:
        _enum(
            boxes["border"],
            "boxes.border",
            BORDER_TYPES,
        )

    for key in (
        "border_color",
        "text_color",
        "accent_color",
    ):
        if key in boxes:
            _color(
                boxes[key],
                f"boxes.{key}",
            )

    if "padding" in boxes:
        padding = _mapping(
            boxes["padding"],
            "boxes.padding",
        )
        for key in (
            "horizontal",
            "vertical",
        ):
            if key in padding:
                value = _integer(
                    padding[key],
                    f"boxes.padding.{key}",
                )
                if value < 0:
                    _error(
                        f"boxes.padding.{key}",
                        "must be greater than or equal to 0",
                    )

    items = boxes.get("items", [])
    if not isinstance(items, list):
        _error(
            "boxes.items",
            "must be a list",
        )

    for index, item in enumerate(items):
        _validate_box(item, index)

    return config

def _validate_weather(item, path):
    if "location" in item:
        location = _string(item["location"], f"{path}.location")
        if not location:
            _error(f"{path}.location", "must not be empty")

    if "latitude" in item:
        latitude = item["latitude"]
        if not isinstance(latitude, (int, float)):
            _error(f"{path}.latitude", "must be a number")
        elif not -90 <= latitude <= 90:
            _error(f"{path}.latitude", "must be between -90 and 90")

    if "longitude" in item:
        longitude = item["longitude"]
        if not isinstance(longitude, (int, float)):
            _error(f"{path}.longitude", "must be a number")
        elif not -180 <= longitude <= 180:
            _error(f"{path}.longitude", "must be between -180 and 180")

    if "location" not in item and not (
        "latitude" in item and "longitude" in item
    ):
        _error(path, "requires location or latitude and longitude")

def _parse(text, path):
    try:
        config = _yaml().load(text)
    except YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc

    if config is None:
        raise ConfigError(f"{path}: configuration is empty")

    return validate_config(config)


def _default_config():
    return files("dripfetch").joinpath(
        "default_config.yaml",
    ).read_text(encoding="utf-8")


def save_config(config, path=CONFIG_PATH):
    path = Path(path).expanduser()
    validate_config(config)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mode = path.stat().st_mode if path.exists() else 0o644
    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)

            os.chmod(
                temporary,
                mode & 0o777,
            )

            _yaml().dump(
                config,
                file,
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temporary,
            path,
        )

        try:
            directory = os.open(
                path.parent,
                os.O_RDONLY,
            )
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            pass

    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def create_default_config(force=False):
    if CONFIG_PATH.exists() and not force:
        return False

    save_config(
        _parse(
            _default_config(),
            "default_config.yaml",
        ),
        CONFIG_PATH,
    )

    return True


def load_config(path=None):
    path = Path(path or CONFIG_PATH).expanduser()

    if not path.exists():
        if path != CONFIG_PATH:
            raise FileNotFoundError(
                f"Configuration file not found: {path}",
            )
        create_default_config()

    try:
        text = path.read_text(
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(
            f"{path}: cannot read configuration: {exc}",
        ) from exc

    return _parse(
        text,
        path,
    )