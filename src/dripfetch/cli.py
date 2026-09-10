import argparse
import curses

from . import __version__
from .app import App
from .config import (
    CONFIG_PATH,
    create_default_config,
)


def main():
    parser = argparse.ArgumentParser(
        prog="dripfetch",
        description=(
            "A customizable terminal system information display with animated rain."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""controls:
  q              quit
  space          pause/resume rain
  mouse          select box
  w/a/s/d        move selected box
  esc            deselect selected box
configuration:
  --init-config  restore the default configuration
  --config-path  show the configuration file currently in use
  -c PATH        use a custom configuration file""",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
    )
    parser.add_argument(
        "--config-path",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="PATH",
    )
    args = parser.parse_args()
    if args.init_config:
        create_default_config(force=True)
        print(CONFIG_PATH)
        return
    config_path = args.config or CONFIG_PATH
    if args.config_path:
        print(config_path)
        return
    curses.wrapper(App(config_path).run)
