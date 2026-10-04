"""Connected-display detection for the sysinfo box."""

import re

from .commands import run_command


def format_displays(system):
    """One "Name: resolution" line per connected display."""
    if system == "Darwin":
        return _darwin_displays()

    if system == "Linux":
        return _linux_displays()

    return []


# ---------------------------------------------------------------------------
# macOS (system_profiler)
# ---------------------------------------------------------------------------
def _parse_darwin_displays(output):
    displays = []
    current = None

    for raw in output.splitlines():
        line = raw.strip()

        if raw.startswith("        ") and line.endswith(":"):
            name = line[:-1]

            # system_profiler nests display entries under a
            # "Displays:" section, which itself sits under a
            # section header named for the GPU/chip (e.g.
            # "Apple M1 Pro:", "Apple M3 Max:"). Skip both kinds
            # of header, not just one specific chip.
            if name != "Displays" and not re.match(r"^Apple M\d", name):
                current = {"name": name}
                displays.append(current)

        elif current:
            if line.startswith("Resolution:"):
                current["resolution"] = line.split(":", 1)[1].strip()

            elif line.startswith("UI Looks like:"):
                current["ui"] = line.split(":", 1)[1].strip()

    return displays


def _describe_darwin_display(display):
    name = display["name"]

    if name == "Color LCD":
        name = "MacBook Pro"

    ui = display.get("ui")
    resolution = display.get("resolution", "")

    if ui:
        return f"{name}: {ui.replace('.00Hz', ' Hz')}"

    if name == "MacBook Pro":
        return f"{name}: {resolution.replace(' Retina', '')} @ 120 Hz"

    if resolution:
        return f"{name}: {resolution}"

    return None


def _darwin_displays():
    output = run_command("system_profiler", "SPDisplaysDataType")
    described = (
        _describe_darwin_display(display)
        for display in _parse_darwin_displays(output)
    )
    return [line for line in described if line]


# ---------------------------------------------------------------------------
# Linux (xrandr)
# ---------------------------------------------------------------------------
def _linux_displays():
    output = run_command("xrandr", "--current")

    if not output:
        return []

    lines = []

    for line in output.splitlines():
        if " connected" not in line:
            continue

        parts = line.split()

        if len(parts) < 3:
            continue

        name = parts[0]

        for part in parts[2:]:
            if "x" not in part or "+" not in part:
                continue

            lines.append(f"{name}: {part.split('+', 1)[0]}")
            break

    return lines
