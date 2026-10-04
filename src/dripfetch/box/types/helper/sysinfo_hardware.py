"""CPU, memory and disk readings for the sysinfo box."""

import os

import psutil

from .commands import run_command
from .units import format_bytes

# Any externally-mounted volume on macOS, not one specific drive name.
_MAC_EXTERNAL_PREFIX = "/Volumes/"


def cpu_summary(brand, cores):
    try:
        frequency = psutil.cpu_freq()

        if frequency:
            frequency = f"{frequency.current / 1000:.2f} GHz"
        else:
            frequency = "Unknown"

    except (AttributeError, OSError, RuntimeError, TypeError):
        frequency = "Unknown"

    try:
        usage = psutil.cpu_percent()
    except (OSError, RuntimeError):
        usage = 0

    return f"{brand} ({cores}) @ {frequency} ({usage:.0f}%)"


def memory_summary():
    try:
        memory = psutil.virtual_memory()
    except (OSError, RuntimeError):
        return "Unknown"

    return (
        f"{format_bytes(memory.used)} / "
        f"{format_bytes(memory.total)} "
        f"({memory.percent:.0f}%)"
    )


def _statvfs_usage(path):
    try:
        stat = os.statvfs(path)
    except OSError:
        return None

    total = stat.f_blocks * stat.f_frsize
    available = stat.f_bavail * stat.f_frsize
    used = total - available

    return (
        format_bytes(used),
        format_bytes(total),
        used / total * 100 if total else 0,
    )


def _df_rows():
    """Yield (mount, used, total, percent) for each parsable `df -k` row."""
    for line in run_command("df", "-k").splitlines()[1:]:
        parts = line.split()

        if len(parts) < 6:
            continue

        mount = " ".join(parts[8:]) if len(parts) > 8 else parts[5]

        try:
            used = int(parts[2]) * 1024
            total = int(parts[1]) * 1024
            percent = int(parts[4].rstrip("%"))
        except ValueError:
            continue

        yield mount, format_bytes(used), format_bytes(total), percent


def disk_usage(system):
    """List of (mount, used, total, percent) for the volumes worth showing."""
    if system == "Darwin":
        results = []
        root = _statvfs_usage("/")

        if root:
            results.append(("/", *root))

        results.extend(
            row for row in _df_rows() if row[0].startswith(_MAC_EXTERNAL_PREFIX)
        )
        return results

    for row in _df_rows():
        if row[0] == "/":
            return [row]

    return []
