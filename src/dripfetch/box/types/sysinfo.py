import platform
import threading

import psutil

from ..base import BaseBox
from .helper import sysinfo_system as system_info
from .helper import validation
from .helper.sysinfo_colors import color_line
from .helper.sysinfo_display import format_displays
from .helper.sysinfo_hardware import cpu_summary, disk_usage, memory_summary
from .helper.sysinfo_lines import build_lines
from .helper.sysinfo_network import battery, ip_address


class SysInfoBox(BaseBox):
    SECTIONS = (
        "system",
        "display",
        "hardware",
        "disk",
        "connectivity",
    )
    ALIGNMENT = "left"

    def __init__(self, stdscr, config, boxes_config, colors, renderer):
        super().__init__(stdscr, config, boxes_config, colors, renderer)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.system = platform.system()

        self.sections = dict.fromkeys(self.SECTIONS, True)
        self.sections.update(self.config.get("sections", {}))

        self.static = {
            "os": system_info.os_name(self.system),
            "host": system_info.host_name(self.system),
            "kernel": system_info.kernel(self.system),
            "packages": "Loading...",
            "shell": "Loading...",
            "displays": [],
            "de": system_info.desktop_environment(self.system),
            "terminal": system_info.terminal_name(),
            "cpu_brand": "Loading...",
            "cpu_cores": "Loading...",
        }

        self.lines = ["Loading..."]

        self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.thread.start()

    @classmethod
    def validate_config(cls, item, path):
        if "sections" not in item:
            return
        sections_path = f"{path}.sections"
        sections = validation.mapping(item["sections"], sections_path)
        for key, value in sections.items():
            if key not in cls.SECTIONS:
                validation.error(
                    sections_path,
                    f"unknown section '{key}', must be one of: "
                    f"{', '.join(sorted(cls.SECTIONS))}",
                )
            validation.boolean(value, f"{sections_path}.{key}")

    def _enabled(self, section):
        return self.sections.get(section, True)

    # ------------------------------------------------------------------
    # Data collection (runs on the background thread)
    # ------------------------------------------------------------------
    def _collect_static(self):
        values = {}

        if self._enabled("system"):
            values["packages"] = system_info.packages(self.system)
            values["shell"] = system_info.shell_version()

        if self._enabled("display"):
            values["displays"] = format_displays(self.system)

        if self._enabled("hardware"):
            values["cpu_brand"] = platform.processor() or "Unknown"
            values["cpu_cores"] = str(psutil.cpu_count(logical=True) or "Unknown")

        with self.lock:
            self.static.update(values)

    def _collect_live(self, static):
        live = {
            "uptime": "Unknown",
            "cpu": "Unknown",
            "memory": "Unknown",
            "disks": None,
            "ip": "Unknown",
            "battery": "Unknown",
            "connected": False,
            "adapter": "Unknown",
        }

        if self._enabled("system"):
            live["uptime"] = system_info.uptime()

        if self._enabled("hardware"):
            live["cpu"] = cpu_summary(static["cpu_brand"], static["cpu_cores"])
            live["memory"] = memory_summary()

        if self._enabled("disk"):
            live["disks"] = disk_usage(self.system)

        if self._enabled("connectivity"):
            live["ip"] = ip_address()
            live["battery"], live["connected"], live["adapter"] = battery()

        return live

    def _refresh(self):
        with self.lock:
            static = dict(self.static)

        lines = build_lines(self._enabled, static, self._collect_live(static))

        with self.lock:
            self.lines = lines

        # content() is cached by BaseBox (see base.py) -- this runs on the
        # background refresh thread, so flag the cache stale instead of
        # recomputing the colored segments here.
        self.mark_dirty()

    def _initialize_data(self):
        try:
            self._collect_static()
            self._refresh()
        except Exception:
            pass

    def _refresh_loop(self):
        # _collect_static() and the first _refresh() both shell out to
        # system_profiler / brew / dpkg-query / df, each with several
        # seconds of timeout headroom. Doing that here, on the background
        # thread, means constructing this box never blocks app startup.
        self._initialize_data()
        while not self.stop_event.wait(1):
            try:
                self._refresh()
            except Exception:
                continue

    # ------------------------------------------------------------------
    # BaseBox interface
    # ------------------------------------------------------------------
    def content(self):
        with self.lock:
            lines = list(self.lines)

        return [color_line(line, self.colors) for line in lines]

    def close(self):
        self.stop_event.set()

        if self.thread.is_alive():
            self.thread.join(timeout=1)
