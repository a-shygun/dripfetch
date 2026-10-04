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


def _characters(value, path):
    if isinstance(value, str):
        if not value:
            _error(path, "must not be empty")
        return
    if not isinstance(value, list) or not value:
        _error(path, "must be a non-empty string or list of strings")
    for index, character in enumerate(value):
        character_path = f"{path}[{index}]"
        _string(character, character_path)
        if not character:
            _error(character_path, "must not be empty")


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
            _error("rain.intensity", "must be greater than or equal to 0")
    if "character" in rain:
        _characters(rain["character"], "rain.character")
    for key, value_type in (
        ("colors", "color"),
        ("speeds", "integer"),
        ("lengths", "integer"),
    ):
        if key in rain:
            _weighted_list(rain[key], f"rain.{key}", value_type)
    from ..box.validation import validate_box_config  # noqa: PLC0415

    validate_box_config(config)

    return config


def _parse(text, path):
    try:
        config = _yaml().load(text)
    except YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    if config is None:
        raise ConfigError(f"{path}: configuration is empty")
    return validate_config(config)


def _default_config():
    return (
        files("dripfetch")
        .joinpath("assets", "configs", "0_default.yaml")
        .read_text(encoding="utf-8")
    )


def save_config(config, path=CONFIG_PATH):
    path = Path(path).expanduser()
    validate_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
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
            os.chmod(temporary, mode & 0o777)
            _yaml().dump(config, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        try:
            directory = os.open(path.parent, os.O_RDONLY)
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
        _parse(_default_config(), "assets/configs/0_default.yaml"),
        CONFIG_PATH,
    )
    return True


def load_config(path=None):
    path = Path(path or CONFIG_PATH).expanduser()
    if not path.exists():
        if path != CONFIG_PATH:
            raise FileNotFoundError(f"Configuration file not found: {path}")
        create_default_config()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read configuration: {exc}") from exc
    return _parse(text, path)
