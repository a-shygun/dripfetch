"""Static and slow-changing facts about the operating system and shell."""

import os
import platform
import shutil
import time

import psutil

from .commands import run_command
from .os_release import read_os_release

_LINUX_PACKAGE_MANAGERS = (
    ("pacman", ("pacman", "-Qq")),
    ("dpkg-query", ("dpkg-query", "-W", "-f", "${binary:Package}\n")),
    ("rpm", ("rpm", "-qa")),
    ("apk", ("apk", "info")),
)


def kernel(system):
    return f"{system} {platform.release()}"


def os_name(system):
    if system == "Darwin":
        return f"macOS {platform.mac_ver()[0]} {platform.machine()}"

    if system == "Windows":
        return f"Windows {platform.release()} {platform.machine()}"

    if system == "Linux":
        data = read_os_release()
        name = data.get("PRETTY_NAME") or data.get("NAME")
        if name:
            return f"{name} {platform.machine()}"

    return f"{system} {platform.release()} {platform.machine()}"


def uptime():
    try:
        seconds = max(0, int(time.time() - psutil.boot_time()))
    except (OSError, RuntimeError):
        return "Unknown"

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60

    if days:
        return f"{days}d {hours}h {minutes}m"

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


def host_name(system):
    if system == "Darwin":
        # `sysctl hw.model` only gives a model identifier (e.g.
        # "MacBookPro18,1"), not a marketing name, and there's no
        # built-in way to map one to the other without shipping a
        # (large, ever-growing) identifier table. system_profiler's
        # "Model Name" is coarser ("MacBook Pro" with no size/year)
        # but it's accurate for every Mac, not just one.
        output = run_command("system_profiler", "SPHardwareDataType")

        for line in output.splitlines():
            if line.strip().startswith("Model Name:"):
                return line.split(":", 1)[1].strip()

    elif system == "Linux":
        model = run_command(
            "cat", "/sys/devices/virtual/dmi/id/product_name"
        ) or run_command("hostnamectl", "hostname")

        if model:
            return model

    return platform.node() or "Unknown"


def packages(system):
    if system == "Darwin":
        if not shutil.which("brew"):
            return "Unknown"

        output = run_command("brew", "list", "--formula")
        return f"{len(output.splitlines())} brew formulas"

    if system == "Linux":
        for command, args in _LINUX_PACKAGE_MANAGERS:
            if not shutil.which(command):
                continue

            output = run_command(*args)
            return f"{len(output.splitlines())} packages"

    return "Unknown"


def shell_version():
    shell = os.path.basename(os.environ.get("SHELL", ""))

    if not shell:
        return "Unknown"

    version = run_command(shell, "--version")

    if version:
        version = version.splitlines()[0]

        if " " in version:
            version = version.split(" ", 1)[1]

        version = version.split(" (", 1)[0]

    return f"{shell} {version}".strip()


def desktop_environment(system):
    if system == "Darwin":
        return "Liquid Glass"

    if system == "Linux":
        return (
            os.environ.get("XDG_CURRENT_DESKTOP")
            or os.environ.get("XDG_SESSION_DESKTOP")
            or os.environ.get("DESKTOP_SESSION")
            or "Unknown"
        )

    if system == "Windows":
        return "Windows"

    return "Unknown"


def terminal_name():
    name = os.environ.get("TERM_PROGRAM", "")

    if name == "iTerm.app":
        name = "iTerm"

    if not name:
        name = os.environ.get("TERM", "")

    version = os.environ.get("TERM_PROGRAM_VERSION", "")

    return f"{name} {version}".strip() or "Unknown"
