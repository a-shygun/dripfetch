import argparse
import curses
from importlib.resources import files

from .. import __version__
from .app import App
from .config import CONFIG_PATH, create_default_config


def get_box_types():
    path = files("dripfetch").joinpath("box", "types")
    return sorted(
        item.name
        for item in path.iterdir()
        if item.is_dir() and not item.name.startswith("_")
    )


def get_logos():
    path = files("dripfetch").joinpath("assets", "logos")
    return sorted(
        item.stem for item in path.iterdir() if item.is_file() and item.suffix == ".txt"
    )


def print_list(title, items):
    print(f"{title}:")
    for item in items:
        print(f"  {item}")


def print_logo(name):
    path = files("dripfetch").joinpath(
        "assets",
        "logos",
        f"{name}.txt",
    )
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
  -c PATH        use a custom configuration file
information:
  --list-logos   list available logos
  --print-logo   print a logo
  --list-boxes   list available box types
""",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
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
        metavar="PATH",
        help="use a custom configuration file",
    )
    parser.add_argument(
        "--list-logos",
        action="store_true",
        help="list available logos",
    )
    parser.add_argument(
        "--print-logo",
        metavar="NAME",
        help="print a logo",
    )
    parser.add_argument(
        "--list-boxes",
        action="store_true",
        help="list available box types",
    )
    return parser


def main():
    logos = get_logos()
    box_types = get_box_types()
    args = build_parser().parse_args()
    if args.version_raw:
        print(__version__)
        return
    if args.list_logos:
        print_list("available logos", logos)
        return
    if args.print_logo:
        raise SystemExit(print_logo(args.print_logo))
    if args.list_boxes:
        print_list("available box types", box_types)
        return
    if args.init_config:
        create_default_config(force=True)
        print(CONFIG_PATH)
        return
    config_path = args.config or CONFIG_PATH
    if args.config_path:
        print(config_path)
        return
    curses.wrapper(App(config_path).run)


if __name__ == "__main__":
    main()
