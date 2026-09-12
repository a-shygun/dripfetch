import ipaddress
import os
import platform
import shutil
import socket
import subprocess
import threading
import time

import psutil

from ..manager import BaseBox


class SysInfoBox(BaseBox):
    LINE_CHARS = "┌─│├└┐┘┤┬┴┼"
    TITLES = {
        "SYSTEM",
        "DISPLAY",
        "HARDWARE",
        "DISK",
        "CONNECTIVITY",
    }
    SECTIONS = (
        "system",
        "display",
        "hardware",
        "disk",
        "connectivity",
    )
    ALIGNMENT = "left"

    def __init__(
        self,
        stdscr,
        config,
        boxes_config,
        colors,
        renderer,
    ):
        super().__init__(
            stdscr,
            config,
            boxes_config,
            colors,
            renderer,
        )

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.system = platform.system()

        self.sections = {
            section: True
            for section in self.SECTIONS
        }
        self.sections.update(
            self.config.get("sections", {})
        )

        self.static = {
            "os": self._os(),
            "host": self._host(),
            "kernel": (
                f"{self.system} "
                f"{platform.release()}"
            ),
            "packages": "Loading...",
            "shell": "Loading...",
            "displays": [],
            "de": self._desktop_environment(),
            "terminal": self._terminal(),
            "cpu_brand": "Loading...",
            "cpu_cores": "Loading...",
        }

        self.lines = []

        self._initialize_data()

        self.thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
        )
        self.thread.start()

    def _enabled(self, section):
        return self.sections.get(
            section,
            True,
        )

    def _command(self, *args):
        try:
            return subprocess.check_output(
                args,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
        except (
            OSError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            return ""

    @staticmethod
    def _bytes(value):
        value = float(value)

        for unit in (
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB",
        ):
            if value < 1024:
                return f"{value:.2f} {unit}"

            value /= 1024

        return f"{value:.2f} PiB"

    def _os(self):
        if self.system == "Darwin":
            version = platform.mac_ver()[0]

            return (
                f"macOS {version} "
                f"{platform.machine()}"
            )

        if self.system == "Windows":
            return (
                f"Windows {platform.release()} "
                f"{platform.machine()}"
            )

        if self.system == "Linux":
            try:
                data = {}

                with open(
                    "/etc/os-release",
                    encoding="utf-8",
                ) as file:
                    for line in file:
                        key, _, value = line.partition("=")
                        data[key] = value.strip().strip('"')

                name = (
                    data.get("PRETTY_NAME")
                    or data.get("NAME")
                )

                if name:
                    return (
                        f"{name} "
                        f"{platform.machine()}"
                    )

            except OSError:
                pass

        return (
            f"{self.system} "
            f"{platform.release()} "
            f"{platform.machine()}"
        )

    def _uptime(self):
        try:
            seconds = max(
                0,
                int(time.time() - psutil.boot_time()),
            )
        except (
            OSError,
            RuntimeError,
        ):
            return "Unknown"

        days, seconds = divmod(
            seconds,
            86400,
        )
        hours, seconds = divmod(
            seconds,
            3600,
        )
        minutes = seconds // 60

        if days:
            return f"{days}d {hours}h {minutes}m"

        if hours:
            return f"{hours}h {minutes}m"

        return f"{minutes}m"

    def _host(self):
        if self.system == "Darwin":
            identifier = self._command(
                "sysctl",
                "-n",
                "hw.model",
            )

            if identifier == "MacBookPro18,1":
                return "MacBook Pro (16-inch, 2021)"

            output = self._command(
                "system_profiler",
                "SPHardwareDataType",
            )

            for line in output.splitlines():
                if line.strip().startswith("Model Name:"):
                    return line.split(
                        ":",
                        1,
                    )[1].strip()

        elif self.system == "Linux":
            model = self._command(
                "cat",
                "/sys/devices/virtual/dmi/id/product_name",
            )

            if model:
                return model

            model = self._command(
                "hostnamectl",
                "hostname",
            )

            if model:
                return model

        return platform.node() or "Unknown"

    def _packages(self):
        if self.system == "Darwin":
            if not shutil.which("brew"):
                return "Unknown"

            output = self._command(
                "brew",
                "list",
                "--formula",
            )

            return (
                f"{len(output.splitlines())} "
                "brew formulas"
            )

        if self.system == "Linux":
            managers = (
                (
                    "pacman",
                    ("pacman", "-Qq"),
                ),
                (
                    "dpkg-query",
                    (
                        "dpkg-query",
                        "-W",
                        "-f",
                        "${binary:Package}\n",
                    ),
                ),
                (
                    "rpm",
                    ("rpm", "-qa"),
                ),
                (
                    "apk",
                    ("apk", "info"),
                ),
            )

            for command, args in managers:
                if not shutil.which(command):
                    continue

                output = self._command(*args)

                return (
                    f"{len(output.splitlines())} "
                    "packages"
                )

        return "Unknown"

    def _shell(self):
        shell = os.path.basename(
            os.environ.get("SHELL", "")
        )

        if not shell:
            return "Unknown"

        version = self._command(
            shell,
            "--version",
        )

        if version:
            version = version.splitlines()[0]

            if " " in version:
                version = version.split(
                    " ",
                    1,
                )[1]

            version = version.split(
                " (",
                1,
            )[0]

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

                if (
                    raw.startswith("        ")
                    and line.endswith(":")
                ):
                    name = line[:-1]

                    if name not in {
                        "Displays",
                        "Apple M1 Pro",
                    }:
                        current = {"name": name}
                        displays.append(current)

                elif current:
                    if line.startswith("Resolution:"):
                        current["resolution"] = (
                            line.split(
                                ":",
                                1,
                            )[1].strip()
                        )

                    elif line.startswith("UI Looks like:"):
                        current["ui"] = (
                            line.split(
                                ":",
                                1,
                            )[1].strip()
                        )

            lines = []

            for display in displays:
                name = display["name"]

                if name == "Color LCD":
                    name = "MacBook Pro"

                ui = display.get("ui")
                resolution = display.get(
                    "resolution",
                    "",
                )

                if ui:
                    lines.append(
                        f"{name}: "
                        f"{ui.replace('.00Hz', ' Hz')}"
                    )

                elif name == "MacBook Pro":
                    lines.append(
                        f"{name}: "
                        f"{resolution.replace(' Retina', '')}"
                        " @ 120 Hz"
                    )

                elif resolution:
                    lines.append(
                        f"{name}: {resolution}"
                    )

            return lines

        if self.system == "Linux":
            output = self._command(
                "xrandr",
                "--current",
            )

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
                        f"{name}: "
                        f"{part.split('+', 1)[0]}"
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
                frequency = (
                    f"{frequency.current / 1000:.2f} GHz"
                )
            else:
                frequency = "Unknown"

        except (
            AttributeError,
            OSError,
            RuntimeError,
            TypeError,
        ):
            frequency = "Unknown"

        try:
            usage = psutil.cpu_percent()
        except (
            OSError,
            RuntimeError,
        ):
            usage = 0

        return (
            f"{brand} ({cores}) @ "
            f"{frequency} ({usage:.0f}%)"
        )

    def _memory(self):
        try:
            memory = psutil.virtual_memory()
        except (
            OSError,
            RuntimeError,
        ):
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

        total = (
            stat.f_blocks
            * stat.f_frsize
        )
        available = (
            stat.f_bavail
            * stat.f_frsize
        )
        used = total - available

        return (
            self._bytes(used),
            self._bytes(total),
            used / total * 100
            if total
            else 0,
        )

    def _disks(self):
        results = []

        if self.system == "Darwin":
            disk = self._disk_stats("/")

            if disk:
                results.append(
                    ("/", *disk)
                )

            mounts = {"/Volumes/RYX "}

            for line in self._command(
                "df",
                "-k",
            ).splitlines()[1:]:
                parts = line.split()

                if len(parts) < 6:
                    continue

                mount = (
                    " ".join(parts[8:])
                    if len(parts) > 8
                    else parts[5]
                )

                if not any(
                    mount.startswith(prefix)
                    for prefix in mounts
                ):
                    continue

                try:
                    used = int(parts[2]) * 1024
                    total = int(parts[1]) * 1024
                    percent = int(
                        parts[4].rstrip("%")
                    )
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

        for line in self._command(
            "df",
            "-k",
        ).splitlines()[1:]:
            parts = line.split()

            if len(parts) < 6:
                continue

            mount = (
                " ".join(parts[8:])
                if len(parts) > 8
                else parts[5]
            )

            if mount != "/":
                continue

            try:
                used = int(parts[2]) * 1024
                total = int(parts[1]) * 1024
                percent = int(
                    parts[4].rstrip("%")
                )
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
        except (
            OSError,
            RuntimeError,
        ):
            return "Unknown"

        preferred = (
            "en0",
            "eth0",
            "wlan0",
        )

        names = (
            preferred
            + tuple(
                name
                for name in interfaces
                if name not in preferred
            )
        )

        for name in names:
            for address in interfaces.get(
                name,
                [],
            ):
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

                return (
                    f"{address.address}/{prefix}"
                )

        return "Unknown"

    def _battery(self):
        try:
            battery = psutil.sensors_battery()
        except (
            AttributeError,
            OSError,
        ):
            battery = None

        if battery is None:
            return (
                "Unknown",
                False,
                "Unknown",
            )

        connected = battery.power_plugged

        return (
            f"{battery.percent:.0f}",
            connected,
            (
                "AC Power"
                if connected
                else "Battery"
            ),
        )

    def _desktop_environment(self):
        if self.system == "Darwin":
            return "Liquid Glass"

        if self.system == "Linux":
            return (
                os.environ.get(
                    "XDG_CURRENT_DESKTOP"
                )
                or os.environ.get(
                    "XDG_SESSION_DESKTOP"
                )
                or os.environ.get(
                    "DESKTOP_SESSION"
                )
                or "Unknown"
            )

        if self.system == "Windows":
            return "Windows"

        return "Unknown"

    def _terminal(self):
        name = os.environ.get(
            "TERM_PROGRAM",
            "",
        )

        if name == "iTerm.app":
            name = "iTerm"

        if not name:
            name = os.environ.get(
                "TERM",
                "",
            )

        version = os.environ.get(
            "TERM_PROGRAM_VERSION",
            "",
        )

        return (
            f"{name} {version}".strip()
            or "Unknown"
        )

    def _collect_static(self):
        values = {}

        if self._enabled("system"):
            values["packages"] = self._packages()
            values["shell"] = self._shell()

        if self._enabled("display"):
            values["displays"] = (
                self._format_displays()
            )

        if self._enabled("hardware"):
            values["cpu_brand"] = (
                platform.processor()
                or "Unknown"
            )
            values["cpu_cores"] = str(
                psutil.cpu_count(
                    logical=True
                )
                or "Unknown"
            )

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
        lines = []

        if self._enabled("system"):
            lines.extend(
                (
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
                )
            )

        if self._enabled("display"):
            lines.append("├─ DISPLAY")

            displays = self.static["displays"]

            if displays:
                for index, display in enumerate(
                    displays
                ):
                    prefix = (
                        "└─"
                        if index == len(displays) - 1
                        else "├─"
                    )
                    lines.append(
                        f"│  {prefix} {display}"
                    )
            else:
                lines.append(
                    "│  └─ Loading..."
                )

            lines.append("│")

        if self._enabled("hardware"):
            lines.extend(
                (
                    "├─ HARDWARE",
                    f"│  ├─ CPU        {cpu}",
                    f"│  └─ Memory     {memory}",
                    "│",
                )
            )

        if self._enabled("disk"):
            lines.append("├─ DISK")

            if disks is None:
                lines.append(
                    "│  └─ Loading..."
                )

            elif disks:
                for index, (
                    name,
                    used,
                    total,
                    percent,
                ) in enumerate(disks):
                    prefix = (
                        "└─"
                        if index == len(disks) - 1
                        else "├─"
                    )

                    label = (
                        "Internal"
                        if name == "/"
                        else os.path.basename(name)
                    )

                    lines.append(
                        f"│  {prefix} "
                        f"{label:<12} "
                        f"{used} / {total} "
                        f"({percent:.0f}%)"
                    )

            else:
                lines.append(
                    "│  └─ Unknown"
                )

            lines.append("│")

        if self._enabled("connectivity"):
            lines.extend(
                (
                    "├─ CONNECTIVITY",
                    f"│  ├─ Network    {ip}",
                    f"│  ├─ Battery    {battery}% "
                    f"[{'AC connected' if connected else 'Battery'}]",
                    f"│  └─ Adapter    {adapter}",
                )
            )

        if lines and lines[-1] == "│":
            lines.pop()

        return lines

    def _refresh(self):
        if self._enabled("hardware"):
            cpu = self._cpu()
            memory = self._memory()
        else:
            cpu = "Unknown"
            memory = "Unknown"

        disks = self._disks() if self._enabled("disk") else None

        if self._enabled("connectivity"):
            ip = self._network()
            battery, connected, adapter = (
                self._battery()
            )
        else:
            ip = "Unknown"
            battery = "Unknown"
            connected = False
            adapter = "Unknown"

        lines = self._build_lines(
            cpu,
            memory,
            disks,
            ip,
            battery,
            connected,
            adapter,
        )

        with self.lock:
            self.lines = lines

    def _initialize_data(self):
        try:
            self._collect_static()
            self._refresh()
        except Exception:
            pass

    def _refresh_loop(self):
        while not self.stop_event.wait(1):
            try:
                self._refresh()
            except Exception:
                continue

    def content(self):
        with self.lock:
            lines = list(self.lines)

        return [
            self._color_line(line)
            for line in lines
        ]

    def _color_line(self, line):
        title = self._title(line)

        if title:
            prefix = line[: -len(title)]

            segments = self._color_text(
                prefix,
                self.colors.line,
                self.colors.text,
            )
            segments.append(
                (title, self.colors.title)
            )

            return segments

        return self._color_text(
            line,
            self.colors.line,
            self.colors.text,
        )

    def _title(self, line):
        for title in self.TITLES:
            if line.endswith(title):
                return title

        return None

    def _color_text(
        self,
        text,
        line_color,
        text_color,
    ):
        if not text:
            return []

        segments = []

        start = 0

        current = line_color if text[0] in self.LINE_CHARS else text_color

        for index in range(1, len(text)):
            color = line_color if text[index] in self.LINE_CHARS else text_color

            if color == current:
                continue

            segments.append(
                (
                    text[start:index],
                    current,
                )
            )

            start = index
            current = color

        segments.append(
            (
                text[start:],
                current,
            )
        )

        return segments

    def close(self):
        self.stop_event.set()

        if self.thread.is_alive():
            self.thread.join(timeout=1)