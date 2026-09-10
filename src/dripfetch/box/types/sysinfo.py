import ipaddress
import os
import platform
import socket
import subprocess
import threading
import time

import psutil

from ..base import BaseBox


class SysInfoBox(BaseBox):
    LINE_CHARS = set("┌─│├└┐┘┤┬┴┼")
    TITLES = {"SYSTEM", "DISPLAY", "HARDWARE", "DISK", "CONNECTIVITY"}

    def __init__(self, stdscr, config, boxes_config, colors, renderer):
        super().__init__(stdscr, config, boxes_config, colors, renderer)
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.static = {
            "os": f"macOS {platform.mac_ver()[0]} {platform.machine()}",
            "host": "Loading...",
            "kernel": f"Darwin {platform.release()}",
            "packages": "Loading...",
            "shell": "Loading...",
            "displays": [],
            "de": "Liquid Glass",
            "terminal": self._terminal(),
            "cpu_brand": "Loading...",
            "cpu_cores": "Loading...",
            "memory_total": 0,
        }
        self.lines = self._build_lines(
            "Loading...",
            "Loading...",
            [],
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
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    def _bytes(self, value):
        value = float(value)

        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024

        return f"{value:.2f} PiB"

    def _uptime(self):
        try:
            seconds = int(time.time() - psutil.boot_time())
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
        identifier = self._command("sysctl", "-n", "hw.model")

        if identifier == "MacBookPro18,1":
            return "MacBook Pro (16-inch, 2021)"

        model = "Unknown"

        for line in self._command(
            "system_profiler",
            "SPHardwareDataType",
        ).splitlines():
            line = line.strip()

            if line.startswith("Model Name:"):
                model = line.split(":", 1)[1].strip()
                break

        return model

    def _packages(self):
        output = self._command("brew", "list", "--formula")
        return f"{len(output.splitlines()) if output else 0} brew formulas"

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
        displays = []
        current = None

        for raw in self._command(
            "system_profiler",
            "SPDisplaysDataType",
        ).splitlines():
            line = raw.strip()

            if raw.startswith("        ") and line.endswith(":"):
                name = line[:-1]

                if name not in {"Displays", "Apple M1 Pro"}:
                    current = {"name": name}
                    displays.append(current)

            elif current and line.startswith("Resolution:"):
                current["resolution"] = line.split(":", 1)[1].strip()

            elif current and line.startswith("UI Looks like:"):
                current["ui"] = line.split(":", 1)[1].strip()

        lines = []

        for display in displays:
            name = "MacBook Pro" if display["name"] == "Color LCD" else display["name"]
            resolution = display.get("resolution", "")
            ui = display.get("ui")

            if ui:
                lines.append(f"{name}: {ui.replace('.00Hz', ' Hz')}")
            elif name == "MacBook Pro":
                lines.append(f"{name}: {resolution.replace(' Retina', '')} @ 120 Hz")
            elif resolution:
                lines.append(f"{name}: {resolution}")

        return lines

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
        values = {}

        for line in self._command("vm_stat").splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            try:
                values[key] = int(value.strip().rstrip("."))
            except ValueError:
                pass

        total = self.static["memory_total"]

        if not total:
            return "Unknown"

        available = (
            sum(
                values.get(key, 0)
                for key in (
                    "Pages free",
                    "Pages inactive",
                    "Pages speculative",
                )
            )
            * 4096
        )

        used = max(0, total - available)

        return f"{self._bytes(used)} / {self._bytes(total)} ({used / total * 100:.0f}%)"

    def _disks(self):
        results = []
        seen = set()

        for line in self._command("df", "-k").splitlines()[1:]:
            parts = line.split()

            if len(parts) < 6:
                continue

            mount = " ".join(parts[8:]) if len(parts) > 8 else parts[5]

            if mount != "/" and not mount.startswith("/Volumes/RYX "):
                continue

            if mount in seen:
                continue

            try:
                used = int(parts[2]) * 1024
                total = int(parts[1]) * 1024
                percent = int(parts[4].rstrip("%"))
            except ValueError:
                continue

            seen.add(mount)
            results.append((mount, self._bytes(used), self._bytes(total), percent))

        return results

    def _network(self):
        try:
            addresses = psutil.net_if_addrs().get("en0", [])
        except (OSError, RuntimeError):
            return "Unknown"

        for address in addresses:
            if address.family != socket.AF_INET:
                continue

            try:
                prefix = ipaddress.IPv4Network(f"0.0.0.0/{address.netmask}").prefixlen
            except ValueError:
                continue

            return f"{address.address}/{prefix}"

        return "Unknown"

    def _battery(self):
        percent = "Unknown"
        connected = False
        adapter = "Unknown"

        for line in self._command(
            "system_profiler",
            "SPPowerDataType",
        ).splitlines():
            line = line.strip()

            if line.startswith("State of Charge (%):"):
                percent = line.split(":", 1)[1].strip()

            elif line.startswith("Connected:"):
                connected = line.split(":", 1)[1].strip() == "Yes"

            elif line.startswith("Wattage (W):"):
                adapter = f"{line.split(':', 1)[1].strip()}W USB-C Power Adapter"

        return percent, connected, adapter

    def _terminal(self):
        name = os.environ.get("TERM_PROGRAM", "Unknown")
        version = os.environ.get("TERM_PROGRAM_VERSION", "")

        if name == "iTerm.app":
            name = "iTerm"

        return f"{name} {version}".strip()

    def _set_static(self, key, value):
        with self.lock:
            self.static[key] = value

    def _collect_static(self):
        values = {
            "host": self._host(),
            "packages": self._packages(),
            "shell": self._shell(),
            "cpu_brand": self._command(
                "sysctl",
                "-n",
                "machdep.cpu.brand_string",
            )
            or "Unknown",
            "cpu_cores": self._command(
                "sysctl",
                "-n",
                "hw.ncpu",
            )
            or "Unknown",
            "displays": self._format_displays(),
        }

        try:
            values["memory_total"] = int(
                self._command(
                    "sysctl",
                    "-n",
                    "hw.memsize",
                )
            )
        except (TypeError, ValueError):
            values["memory_total"] = 0

        with self.lock:
            self.static.update(values)

    def _section(self, title, items):
        lines = [f"├─ {title}"]

        for index, item in enumerate(items):
            prefix = "└─" if index == len(items) - 1 else "├─"
            lines.append(f"│  {prefix} {item}")

        return lines

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

        lines.extend(
            self._section("DISPLAY", displays)
            if displays
            else ["├─ DISPLAY", "│  └─ Loading..."]
        )

        lines.extend(
            [
                "│",
                "├─ HARDWARE",
                f"│  ├─ CPU        {cpu}",
                f"│  └─ Memory     {memory}",
                "│",
                "├─ DISK",
            ]
        )

        if disks:
            for index, (mount, used, total, percent) in enumerate(disks):
                name = "/" if mount == "/" else mount.removeprefix("/Volumes/RYX ")
                prefix = "└─" if index == len(disks) - 1 else "├─"

                lines.append(f"│  {prefix} {name:<10} {used} / {total} ({percent}%)")
        else:
            lines.append("│  └─ Loading...")

        lines.extend(
            [
                "│",
                "├─ CONNECTIVITY",
                f"│  ├─ Network    {ip}",
                f"│  ├─ Battery    {battery}% "
                f"[{'AC connected' if connected else 'Battery'}]",
                f"│  └─ Adapter    {adapter}",
            ]
        )

        return lines

    def _refresh(self):
        with self.lock:
            cpu_brand = self.static["cpu_brand"]
            cpu_cores = self.static["cpu_cores"]
            memory_total = self.static["memory_total"]
            static = self.static.copy()

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

        cpu = f"{cpu_brand} ({cpu_cores}) @ {frequency} ({usage:.0f}%)"

        values = {}

        for line in self._command("vm_stat").splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            try:
                values[key] = int(value.strip().rstrip("."))
            except ValueError:
                pass

        if memory_total:
            available = (
                sum(
                    values.get(key, 0)
                    for key in (
                        "Pages free",
                        "Pages inactive",
                        "Pages speculative",
                    )
                )
                * 4096
            )
            used = max(0, memory_total - available)
            memory = (
                f"{self._bytes(used)} / {self._bytes(memory_total)} "
                f"({used / memory_total * 100:.0f}%)"
            )
        else:
            memory = "Unknown"

        disks = self._disks()
        ip = self._network()
        battery, connected, adapter = self._battery()

        with self.lock:
            old_static = self.static
            self.static = static
            self.lines = self._build_lines(
                cpu,
                memory,
                disks,
                ip,
                battery,
                connected,
                adapter,
            )
            self.static = old_static

    def _initialize(self):
        try:
            self._collect_static()
            self._refresh()
        except Exception:
            pass

        while not self.stop_event.wait(1):
            try:
                self._refresh()
            except Exception:
                pass

    def _line_type(self, line):
        stripped = line.lstrip("│ ")

        if stripped.startswith(("┌─", "├─")):
            if stripped[2:].strip() in self.TITLES:
                return "title"

        return "text"

    def _draw_line(self, x, y, line):
        if not line:
            return

        if self._line_type(line) == "title":
            self.renderer.draw(x, y, line, self.colors.title)
            return

        index = 0

        while index < len(line):
            if line[index] in self.LINE_CHARS:
                start = index

                while index < len(line) and line[index] in self.LINE_CHARS:
                    index += 1

                self.renderer.draw(
                    x + start,
                    y,
                    line[start:index],
                    self.colors.line,
                )
            else:
                start = index

                while index < len(line) and line[index] not in self.LINE_CHARS:
                    index += 1

                self.renderer.draw(
                    x + start,
                    y,
                    line[start:index],
                    self.colors.text,
                )

    def dimensions(self):
        with self.lock:
            lines = self.lines[:]

        return (
            max((len(line) for line in lines), default=0),
            len(lines),
        )

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
