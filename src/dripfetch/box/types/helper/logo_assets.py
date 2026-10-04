"""Locating, detecting and loading bundled ASCII logos."""

import platform
from importlib.resources import files

from .os_release import read_os_release


def _logo_path(name):
    return files("dripfetch").joinpath("assets", "logos", f"{name}.txt")


def find_logo(name):
    """Return ``name`` if a bundled logo with that name exists, else None."""
    if not name:
        return None
    return name if _logo_path(name).is_file() else None


def detect_logo():
    """Pick a bundled logo for the current operating system, if there is one."""
    system = platform.system()

    if system == "Darwin":
        return find_logo("macos")

    if system == "Windows":
        return find_logo("windows")

    if system == "Linux":
        distro = read_os_release().get("ID", "").lower()
        if distro:
            return find_logo(distro)

    return None


def load_logo(name):
    path = _logo_path(name)
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines()
