"""Builds the tree-drawing text lines shown by the sysinfo box."""

import os


def _branch(index, total):
    return "└─" if index == total - 1 else "├─"


def _system_lines(static, uptime):
    return [
        "┌─ SYSTEM",
        f"│  ├─ OS         {static['os']}",
        f"│  ├─ Host       {static['host']}",
        f"│  ├─ Kernel     {static['kernel']}",
        f"│  ├─ Uptime     {uptime}",
        f"│  ├─ Packages   {static['packages']}",
        f"│  ├─ Shell      {static['shell']}",
        f"│  ├─ Terminal   {static['terminal']}",
        f"│  └─ DE         {static['de']}",
        "│",
    ]


def _display_lines(displays):
    lines = ["├─ DISPLAY"]

    if displays:
        for index, display in enumerate(displays):
            lines.append(f"│  {_branch(index, len(displays))} {display}")
    else:
        lines.append("│  └─ Loading...")

    lines.append("│")
    return lines


def _hardware_lines(live):
    return [
        "├─ HARDWARE",
        f"│  ├─ CPU        {live['cpu']}",
        f"│  └─ Memory     {live['memory']}",
        "│",
    ]


def _disk_lines(disks):
    lines = ["├─ DISK"]

    if disks is None:
        lines.append("│  └─ Loading...")

    elif disks:
        for index, (name, used, total, percent) in enumerate(disks):
            label = "Internal" if name == "/" else os.path.basename(name)
            lines.append(
                f"│  {_branch(index, len(disks))} "
                f"{label:<12} "
                f"{used} / {total} "
                f"({percent:.0f}%)"
            )

    else:
        lines.append("│  └─ Unknown")

    lines.append("│")
    return lines


def _connectivity_lines(live):
    state = "AC connected" if live["connected"] else "Battery"
    return [
        "├─ CONNECTIVITY",
        f"│  ├─ Network    {live['ip']}",
        f"│  ├─ Battery    {live['battery']}% [{state}]",
        f"│  └─ Adapter    {live['adapter']}",
    ]


def build_lines(enabled, static, live):
    """Assemble the enabled sections.

    ``enabled`` is a callable section_name -> bool, ``static`` holds values
    that rarely change, and ``live`` the values refreshed every tick.
    """
    lines = []

    if enabled("system"):
        lines.extend(_system_lines(static, live["uptime"]))

    if enabled("display"):
        lines.extend(_display_lines(static["displays"]))

    if enabled("hardware"):
        lines.extend(_hardware_lines(live))

    if enabled("disk"):
        lines.extend(_disk_lines(live["disks"]))

    if enabled("connectivity"):
        lines.extend(_connectivity_lines(live))

    if lines and lines[-1] == "│":
        lines.pop()

    return lines
