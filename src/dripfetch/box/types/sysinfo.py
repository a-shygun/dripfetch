import ipaddress
import os
import platform
import shutil
import socket
import subprocess
import threading
import time

import psutil

from ..base import BaseBox


class SysInfoBox(BaseBox):
    LINE_CHARS = "┌─│├└┐┘┤┬┴┼"
    TITLES = {"SYSTEM", "DISPLAY", "HARDWARE", "DISK", "CONNECTIVITY"}

    def __init__(self, stdscr, config, boxes_config, colors, renderer):
        super().__init__(stdscr, config, boxes_config, colors, renderer)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.system = platform.system()

        self.static = {
            "os": self._os(),
            "host": self._host(),
            "kernel": f"{self.system} {platform.release()}",
            "packages": "Loading...",
            "shell": "Loading...",
            "displays": [],
            "de": self._desktop_environment(),
            "terminal": self._terminal(),
            "cpu_brand": "Loading...",
            "cpu_cores": "Loading...",
        }

        self.lines = self._build_lines(
            "Loading...",
            "Loading...",
            None,
            "Loading...",
            "Loading",
            False,
            "Loading...",
        )

        self.thread = threading.Thread(
            target=self._initialize,
            daemon=True,
        )
        self.thread.start()

    def _command(self, *args):
        try:
            return subprocess.check_output(
                args,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return ""

    def _bytes(self, value):
        value = float(value)

        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024

        return f"{value:.2f} PiB"

    def _os(self):
        if self.system == "Darwin":
            version = platform.mac_ver()[0]
            return f"macOS {version} {platform.machine()}"

        if self.system == "Windows":
            return f"Windows {platform.release()} {platform.machine()}"

        if self.system == "Linux":
            try:
                data = {}

                with open("/etc/os-release", encoding="utf-8") as file:
                    for line in file:
                        key, _, value = line.partition("=")
                        data[key] = value.strip().strip('"')

                name = data.get("PRETTY_NAME") or data.get("NAME")

                if name:
                    return f"{name} {platform.machine()}"
            except OSError:
                pass

        return f"{self.system} {platform.release()} {platform.machine()}"

    def _uptime(self):
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

    def _host(self):
        if self.system == "Darwin":
            identifier = self._command("sysctl", "-n", "hw.model")

            if identifier == "MacBookPro18,1":
                return "MacBook Pro (16-inch, 2021)"

            output = self._command("system_profiler", "SPHardwareDataType")

            for line in output.splitlines():
                if line.strip().startswith("Model Name:"):
                    return line.split(":", 1)[1].strip()

        elif self.system == "Linux":
            model = self._command(
                "cat",
                "/sys/devices/virtual/dmi/id/product_name",
            )

            if model:
                return model

            model = self._command("hostnamectl", "hostname")

            if model:
                return model

        return platform.node() or "Unknown"

    def _packages(self):
        if self.system == "Darwin":
            if not shutil.which("brew"):
                return "Unknown"

            output = self._command("brew", "list", "--formula")
            count = len(output.splitlines())

            return f"{count} brew formulas"

        if self.system == "Linux":
            managers = (
                ("pacman", ("pacman", "-Qq")),
                (
                    "dpkg-query",
                    ("dpkg-query", "-W", "-f", "${binary:Package}\n"),
                ),
                ("rpm", ("rpm", "-qa")),
                ("apk", ("apk", "info")),
            )

            for command, args in managers:
                if not shutil.which(command):
                    continue

                output = self._command(*args)
                return f"{len(output.splitlines())} packages"

        return "Unknown"

    def _shell(self):
        shell = os.path.basename(os.environ.get("SHELL", ""))

        if not shell:
            return "Unknown"

        version = self._command(shell, "--version")

        if version:
            version = version.splitlines()[0]

            if " " in version:
                version = version.split(" ", 1)[1]

            version = version.split(" (", 1)[0]

        return f"{shell} {version}".strip()

    def _format_displays(self):
        if self.system == "Darwin":
            output = self._command(
                "system_profiler",
                "SPDisplaysDataType",
            )

            displays = []
            current = None

            for raw in output.splitlines():
                line = raw.strip()

                if raw.startswith("        ") and line.endswith(":"):
                    name = line[:-1]

                    if name not in {"Displays", "Apple M1 Pro"}:
                        current = {"name": name}
                        displays.append(current)

                elif current:
                    if line.startswith("Resolution:"):
                        current["resolution"] = line.split(
                            ":", 1
                        )[1].strip()
                    elif line.startswith("UI Looks like:"):
                        current["ui"] = line.split(
                            ":", 1
                        )[1].strip()

            lines = []

            for display in displays:
                name = display["name"]

                if name == "Color LCD":
                    name = "MacBook Pro"

                ui = display.get("ui")
                resolution = display.get("resolution", "")

                if ui:
                    lines.append(
                        f"{name}: {ui.replace('.00Hz', ' Hz')}"
                    )
                elif name == "MacBook Pro":
                    lines.append(
                        f"{name}: "
                        f"{resolution.replace(' Retina', '')} @ 120 Hz"
                    )
                elif resolution:
                    lines.append(f"{name}: {resolution}")

            return lines

        if self.system == "Linux":
            output = self._command("xrandr", "--current")

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

                    lines.append(
                        f"{name}: {part.split('+', 1)[0]}"
                    )
                    break

            return lines

        return []

    def _cpu(self):
        brand = self.static["cpu_brand"]
        cores = self.static["cpu_cores"]

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

    def _memory(self):
        try:
            memory = psutil.virtual_memory()
        except (OSError, RuntimeError):
            return "Unknown"

        return (
            f"{self._bytes(memory.used)} / "
            f"{self._bytes(memory.total)} "
            f"({memory.percent:.0f}%)"
        )

    def _disk_stats(self, path):
        try:
            stat = os.statvfs(path)
        except OSError:
            return None

        total = stat.f_blocks * stat.f_frsize
        available = stat.f_bavail * stat.f_frsize
        used = total - available

        return (
            self._bytes(used),
            self._bytes(total),
            used / total * 100 if total else 0,
        )

    def _disks(self):
        results = []

        if self.system == "Darwin":
            disk = self._disk_stats("/")

            if disk:
                results.append(("/", *disk))

            mounts = {"/Volumes/RYX "}

            for line in self._command("df", "-k").splitlines()[1:]:
                parts = line.split()

                if len(parts) < 6:
                    continue

                mount = " ".join(parts[8:]) if len(parts) > 8 else parts[5]

                if not any(mount.startswith(prefix) for prefix in mounts):
                    continue

                try:
                    used = int(parts[2]) * 1024
                    total = int(parts[1]) * 1024
                    percent = int(parts[4].rstrip("%"))
                except ValueError:
                    continue

                results.append(
                    (
                        mount,
                        self._bytes(used),
                        self._bytes(total),
                        percent,
                    )
                )

            return results

        for line in self._command("df", "-k").splitlines()[1:]:
            parts = line.split()

            if len(parts) < 6:
                continue

            mount = " ".join(parts[8:]) if len(parts) > 8 else parts[5]

            if mount != "/":
                continue

            try:
                used = int(parts[2]) * 1024
                total = int(parts[1]) * 1024
                percent = int(parts[4].rstrip("%"))
            except ValueError:
                continue

            results.append(
                (
                    mount,
                    self._bytes(used),
                    self._bytes(total),
                    percent,
                )
            )

            break

        return results

    def _network(self):
        try:
            interfaces = psutil.net_if_addrs()
        except (OSError, RuntimeError):
            return "Unknown"

        preferred = ("en0", "eth0", "wlan0")
        names = preferred + tuple(
            name for name in interfaces if name not in preferred
        )

        for name in names:
            for address in interfaces.get(name, []):
                if (
                    address.family != socket.AF_INET
                    or address.address.startswith("127.")
                ):
                    continue

                try:
                    prefix = ipaddress.IPv4Network(
                        f"0.0.0.0/{address.netmask}"
                    ).prefixlen
                except ValueError:
                    continue

                return f"{address.address}/{prefix}"

        return "Unknown"

    def _battery(self):
        try:
            battery = psutil.sensors_battery()
        except (AttributeError, OSError):
            battery = None

        if battery is None:
            return "Unknown", False, "Unknown"

        connected = battery.power_plugged

        return (
            f"{battery.percent:.0f}",
            connected,
            "AC Power" if connected else "Battery",
        )

    def _desktop_environment(self):
        if self.system == "Darwin":
            return "Liquid Glass"

        if self.system == "Linux":
            return (
                os.environ.get("XDG_CURRENT_DESKTOP")
                or os.environ.get("XDG_SESSION_DESKTOP")
                or os.environ.get("DESKTOP_SESSION")
                or "Unknown"
            )

        if self.system == "Windows":
            return "Windows"

        return "Unknown"

    def _terminal(self):
        name = os.environ.get("TERM_PROGRAM", "")

        if name == "iTerm.app":
            name = "iTerm"

        if not name:
            name = os.environ.get("TERM", "")

        version = os.environ.get("TERM_PROGRAM_VERSION", "")

        return f"{name} {version}".strip() or "Unknown"

    def _collect_static(self):
        values = {
            "packages": self._packages(),
            "shell": self._shell(),
            "cpu_brand": platform.processor() or "Unknown",
            "cpu_cores": str(psutil.cpu_count(logical=True) or "Unknown"),
            "displays": self._format_displays(),
        }

        with self.lock:
            self.static.update(values)

    def _build_lines(
        self,
        cpu,
        memory,
        disks,
        ip,
        battery,
        connected,
        adapter,
    ):
        lines = [
            "┌─ SYSTEM",
            f"│  ├─ OS         {self.static['os']}",
            f"│  ├─ Host       {self.static['host']}",
            f"│  ├─ Kernel     {self.static['kernel']}",
            f"│  ├─ Uptime     {self._uptime()}",
            f"│  ├─ Packages   {self.static['packages']}",
            f"│  ├─ Shell      {self.static['shell']}",
            f"│  ├─ Terminal   {self.static['terminal']}",
            f"│  └─ DE         {self.static['de']}",
            "│",
        ]

        displays = self.static["displays"]

        lines.append("├─ DISPLAY")

        if displays:
            for index, display in enumerate(displays):
                prefix = "└─" if index == len(displays) - 1 else "├─"
                lines.append(f"│  {prefix} {display}")
        else:
            lines.append("│  └─ Loading...")

        lines.extend([
            "│",
            "├─ HARDWARE",
            f"│  ├─ CPU        {cpu}",
            f"│  └─ Memory     {memory}",
            "│",
            "├─ DISK",
        ])

        if disks is None:
            lines.append("│  └─ Loading...")
        elif disks:
            for index, (name, used, total, percent) in enumerate(disks):
                prefix = "└─" if index == len(disks) - 1 else "├─"
                label = "Internal" if name == "/" else os.path.basename(name)

                lines.append(
                    f"│  {prefix} {label:<12} "
                    f"{used} / {total} ({percent:.0f}%)"
                )
        else:
            lines.append("│  └─ Unknown")

        lines.extend([
            "│",
            "├─ CONNECTIVITY",
            f"│  ├─ Network    {ip}",
            f"│  ├─ Battery    {battery}% "
            f"[{'AC connected' if connected else 'Battery'}]",
            f"│  └─ Adapter    {adapter}",
        ])

        return lines

    def _refresh(self):
        cpu = self._cpu()
        memory = self._memory()
        disks = self._disks()
        ip = self._network()
        battery, connected, adapter = self._battery()

        with self.lock:
            self.lines = self._build_lines(
                cpu,
                memory,
                disks,
                ip,
                battery,
                connected,
                adapter,
            )

    def _initialize(self):
        try:
            self._collect_static()
        except Exception:
            pass

        while not self.stop_event.wait(1):
            try:
                self._refresh()
            except Exception:
                continue

    def _line_type(self, line):
        stripped = line.lstrip("│ ")

        if stripped.startswith(("┌─", "├─")):
            return "title" if stripped[2:].strip() in self.TITLES else "text"

        return "text"

    def _draw_line(self, x, y, line):
        if not line:
            return

        if self._line_type(line) == "title":
            self.renderer.draw(x, y, line, self.colors.title)
            return

        start = 0

        while start < len(line):
            is_line = line[start] in self.LINE_CHARS
            end = start + 1

            while end < len(line) and (line[end] in self.LINE_CHARS) == is_line:
                end += 1

            self.renderer.draw(
                x + start,
                y,
                line[start:end],
                self.colors.line if is_line else self.colors.text,
            )

            start = end

    def dimensions(self):
        with self.lock:
            lines = self.lines[:]

        return max(map(len, lines), default=0), len(lines)

    def draw_content(self, x, y, width, height):
        with self.lock:
            lines = self.lines[:]

        for index, line in enumerate(lines[:height]):
            self._draw_line(x, y + index, line[:width])

    def update(self):
        pass

    def close(self):
        self.stop_event.set()

        if self.thread.is_alive():
            self.thread.join(timeout=1)