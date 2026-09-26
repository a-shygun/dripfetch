import argparse
import curses
from importlib.resources import files
from pathlib import Path

from ruamel.yaml import YAML

from .. import __version__
from ..box.manager import get_box_types
from .app import App
from .config import (
    CONFIG_DIR,
    CONFIG_PATH,
    ConfigError,
    create_default_config,
    load_config,
    save_config,
)


def get_logos():
    path = files("dripfetch").joinpath("assets", "logos")
    return sorted(
        item.stem for item in path.iterdir() if item.is_file() and item.suffix == ".txt"
    )


def get_configs():
    """Return packaged YAML configs as (number, stem, resource) tuples."""
    path = files("dripfetch").joinpath("assets", "configs")
    configs = []
    for item in path.iterdir():
        if not item.is_file() or item.suffix != ".yaml":
            continue
        prefix, separator, _ = item.stem.partition("_")
        if separator and prefix.isdigit():
            configs.append((int(prefix), item.stem, item))
    return sorted(configs, key=lambda config: config[0])


def resolve_config(selector):
    """Resolve a preset number/name, while retaining custom path support."""
    selector = str(selector)
    normalized = selector.strip().lower()
    for number, stem, resource in get_configs():
        short_name = stem.partition("_")[2].lower()
        aliases = {str(number), stem.lower(), short_name}
        if number == 0:
            aliases.update({"default", "builtin", "built-in"})
        if normalized not in aliases:
            continue

        # Keep selected presets user-editable without writing into package assets.
        target = CONFIG_DIR / "presets" / f"{stem}.yaml"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(resource.read_text(encoding="utf-8"), encoding="utf-8")
        return target
    return Path(selector).expanduser()


def _bundled_config(selector):
    """Find a packaged preset by number, full name, or short name."""
    normalized = str(selector).strip().lower()
    for number, stem, resource in get_configs():
        short_name = stem.partition("_")[2].lower()
        aliases = {str(number), stem.lower(), short_name}
        if number == 0:
            aliases.update({"default", "builtin", "built-in"})
        if normalized in aliases:
            return stem, resource
    return None


def set_config(selector):
    """Copy a packaged preset into the active user configuration."""
    selected = _bundled_config(selector)
    if selected is None:
        choices = ", ".join(str(number) for number, _, _ in get_configs())
        raise ConfigError(
            f"unknown bundled config '{selector}'; available config numbers: {choices}"
        )
    stem, resource = selected
    yaml = YAML()
    yaml.preserve_quotes = True
    config = yaml.load(resource.read_text(encoding="utf-8"))
    save_config(config, CONFIG_PATH)
    return stem


def set_logo(name):
    """Set the logo on each logo box in the active user configuration."""
    logos = set(get_logos())
    normalized = str(name).strip().lower()
    if normalized not in logos:
        raise ConfigError(f"logo '{name}' not found; use --list-logos to see choices")

    config = load_config(CONFIG_PATH)
    boxes = config.setdefault("boxes", {})
    items = boxes.setdefault("items", [])
    logo_boxes = [item for item in items if item.get("type", "text") == "logo"]
    if logo_boxes:
        for item in logo_boxes:
            item["logo"] = normalized
    else:
        items.append({"type": "logo", "logo": normalized})
    save_config(config, CONFIG_PATH)
    return normalized


def print_list(title, items):
    print(f"{title}:")
    for item in items:
        print(f"  {item}")


def print_logo(name):
    path = files("dripfetch").joinpath("assets", "logos", f"{name}.txt")
    if not path.is_file():
        print(f"error: logo '{name}' not found")
        return 1
    print(path.read_text(encoding="utf-8"), end="")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dripfetch",
        description=(
            "A customizable terminal system information display with animated rain."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
about:
  dripfetch is a customizable terminal system information display.
  Features animated rain, configurable boxes, logos, colors,
  borders, clock, system information, and weather.
controls:
  q              quit
  space          pause/resume rain
  mouse          select box
  w/a/s/d        move selected box
  esc            deselect selected box
configuration:
  --init-config  restore the default configuration
  --config-path  show the configuration file currently in use
  -c NUMBER      use a bundled config by number (0 is the default)
  -c PATH        use a custom configuration file
information:
  --list-logos   list available logos
  --print-logo   print a logo
  --set-logo     persist a logo in the active configuration
  --list-configs list available bundled configurations
  --set-config   persist a bundled configuration as the active one
  --list-boxes   list available box types
""",
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "--version-raw",
        action="store_true",
        help="print the raw version number",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="create or restore the default configuration",
    )
    parser.add_argument(
        "--config-path",
        action="store_true",
        help="show the path of the active configuration file",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="NUMBER|NAME|PATH",
        help="use a bundled config number/name or a custom YAML file",
    )
    parser.add_argument(
        "--list-logos",
        "-list-logos",
        action="store_true",
        help="list available logos",
    )
    parser.add_argument(
        "--list-configs",
        "-list-configs",
        action="store_true",
        help="list bundled configurations (config 0 is the default)",
    )
    parser.add_argument(
        "--print-logo",
        "-print-logo",
        metavar="NAME",
        help="print a logo",
    )
    parser.add_argument(
        "--set-config",
        "-set-config",
        metavar="NUMBER|NAME",
        help="save a bundled config as the active user configuration",
    )
    parser.add_argument(
        "--set-logo",
        "-set-logo",
        metavar="NAME",
        help="save a logo choice in the active user configuration",
    )
    parser.add_argument(
        "--list-boxes",
        action="store_true",
        help="list available box types",
    )
    return parser


def main():
    args = build_parser().parse_args()
    if args.version_raw:
        print(__version__)
        return
    if args.list_logos:
        print_list("available logos", get_logos())
        return
    if args.list_configs:
        entries = []
        for number, stem, _ in get_configs():
            label = "default" if number == 0 else stem.partition("_")[2].replace("_", " ")
            entries.append(f"{number:>2}  {label}  ({stem}.yaml)")
        print_list(
            "available configs (use --config to preview or --set-config to save)",
            entries,
        )
        return
    if args.print_logo:
        raise SystemExit(print_logo(args.print_logo))
    if args.list_boxes:
        print_list("available box types", sorted(get_box_types()))
        return
    if args.init_config:
        create_default_config(force=True)
        print(CONFIG_PATH)
        return
    if args.set_config or args.set_logo:
        try:
            if args.set_config:
                selected = set_config(args.set_config)
                print(f"active config set to {selected} ({CONFIG_PATH})")
            if args.set_logo:
                selected = set_logo(args.set_logo)
                print(f"active logo set to {selected} ({CONFIG_PATH})")
        except (ConfigError, OSError) as exc:
            raise SystemExit(f"error: {exc}") from exc
        return
    config_path = resolve_config(args.config) if args.config else CONFIG_PATH
    if args.config_path:
        print(config_path)
        return
    try:
        curses.wrapper(App(config_path).run)
    except ConfigError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
