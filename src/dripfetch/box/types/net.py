import time
from collections import deque

from ..base import BaseBox
from ...app.terminal import parse_color

# ---------------------------------------------------------------------------
# Braille dot geometry
# ---------------------------------------------------------------------------
# Each character cell is a 2 (columns) x 4 (rows) grid of dots. Standard
# braille dot -> bit mapping, row 0 = top of the cell, row 3 = bottom,
# col 0 = left dot column, col 1 = right dot column.
_BRAILLE_BASE = 0x2800
_DOT_BITS = {
    0: (0x01, 0x08),
    1: (0x02, 0x10),
    2: (0x04, 0x20),
    3: (0x40, 0x80),
}

class NetBox(BaseBox):
    """Download/upload speed box.

    A compact bpytop/btop-style braille throughput graph: download grows
    upward from a shared centerline, upload grows downward, mirrored, so
    the two halves read as one symmetrical waveform. Current rates are
    shown as small labels flanking the graph rather than a header row.

    Config keys
    -----------
    width : int    (default: 20)   graph width in characters.
    height : int   (default: 6)    graph height in characters (split evenly
                                    between the download/upload halves).
    interval : number (default: 1.0)   seconds between samples.
    download_color / upload_color : "#RRGGBBAA"   default to the
        box's text_color (i.e. colors.body) if omitted, same as any
        other box's default text.
    """

    DEFAULT_WIDTH = 20
    DEFAULT_HEIGHT = 6
    MIN_WIDTH = 6
    MIN_HEIGHT = 2

    DEFAULT_INTERVAL = 1.0
    MIN_INTERVAL = 0.1

    # Floor for the shared scale so a perfectly idle link doesn't divide
    # by zero or blow a single packet up to fill the whole graph.
    MIN_SCALE = 1024  # 1 KB/s

    # Fixed-width gutter on the left of the graph that holds the current
    # rate labels, e.g. "\u2193999K/s". Kept tight since the rates are
    # rendered compactly (see _human_rate).
    LABEL_WIDTH = 8

    _UNITS = ("B/s", "K/s", "M/s", "G/s", "T/s")

    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)

        self.width = self._clamp(
            config.get("width", self.DEFAULT_WIDTH),
            self.MIN_WIDTH,
        )
        self.height = self._clamp(
            config.get("height", self.DEFAULT_HEIGHT),
            self.MIN_HEIGHT,
        )
        self.interval = self._clamp_interval(
            config.get("interval", self.DEFAULT_INTERVAL)
        )

        self.download_color = self._color(
            config.get("download_color"), colors.body
        )
        self.upload_color = self._color(
            config.get("upload_color"), colors.body
        )

        # Two samples of history are consumed per character column (one
        # per braille dot-column), so keep 2x the graph width buffered.
        history_length = self.width * 2
        self.dl_history = deque([0] * history_length, maxlen=history_length)
        self.ul_history = deque([0] * history_length, maxlen=history_length)

        self._last_time = None
        self._last_counters = None
        self._reader = self._resolve_reader()

        self.error = None if self._reader else (
            "Network stats unavailable"
        )
        self.download_rate = 0.0
        self.upload_rate = 0.0

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    @classmethod
    def _clamp(cls, value, minimum):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = minimum
        return max(minimum, value)

    @classmethod
    def _clamp_interval(cls, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return cls.DEFAULT_INTERVAL
        return max(cls.MIN_INTERVAL, value)

    @staticmethod
    def _color(value, default):
        if not value:
            return default
        try:
            return parse_color(value)
        except Exception:  # noqa: BLE001
            return default

    # ------------------------------------------------------------------
    # Plug-and-play config validator (called by config.py automatically)
    # ------------------------------------------------------------------
    @classmethod
    def validate_config(cls, item, path):
        from ...app.config import _integer, _number, _string  # noqa: PLC0415

        if "width" in item:
            _integer(item["width"], f"{path}.width")
        if "height" in item:
            _integer(item["height"], f"{path}.height")
        if "interval" in item:
            _number(item["interval"], f"{path}.interval")
        if "download_color" in item:
            _string(item["download_color"], f"{path}.download_color")
        if "upload_color" in item:
            _string(item["upload_color"], f"{path}.upload_color")

    # ------------------------------------------------------------------
    # Counter reading (psutil if available, else /proc/net/dev on Linux)
    # ------------------------------------------------------------------
    def _resolve_reader(self):
        try:
            import psutil  # noqa: PLC0415

            def read_psutil():
                counters = psutil.net_io_counters(pernic=False)
                return counters.bytes_recv, counters.bytes_sent

            # Sanity check it actually works before committing to it.
            read_psutil()
            return read_psutil
        except Exception:  # noqa: BLE001
            pass

        def read_proc():
            recv_total = 0
            sent_total = 0
            with open("/proc/net/dev", "r", encoding="utf-8") as handle:
                lines = handle.readlines()[2:]
            for line in lines:
                iface, _, rest = line.partition(":")
                iface = iface.strip()
                if not iface or iface == "lo":
                    continue
                fields = rest.split()
                if len(fields) < 9:
                    continue
                recv_total += int(fields[0])
                sent_total += int(fields[8])
            return recv_total, sent_total

        try:
            read_proc()
            return read_proc
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # BaseBox interface
    # ------------------------------------------------------------------
    def dimensions(self):
        return self.width + self.LABEL_WIDTH, self.height

    def update(self):
        if not self._reader:
            return

        now = time.monotonic()

        if (
            self._last_time is not None
            and now - self._last_time < self.interval
        ):
            return

        try:
            counters = self._reader()
        except Exception as exc:  # noqa: BLE001
            self.error = f"Network stats unavailable: {exc}"
            return

        if self._last_time is not None and self._last_counters is not None:
            elapsed = now - self._last_time
            if elapsed > 0:
                recv_delta = counters[0] - self._last_counters[0]
                sent_delta = counters[1] - self._last_counters[1]
                # Counters can wrap/reset (interface reset, 32-bit
                # rollover); treat a negative delta as "no data" rather
                # than plotting a nonsensical negative rate.
                self.download_rate = max(0.0, recv_delta / elapsed)
                self.upload_rate = max(0.0, sent_delta / elapsed)
                self.dl_history.append(self.download_rate)
                self.ul_history.append(self.upload_rate)
                self.error = None

        self._last_time = now
        self._last_counters = counters

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    @classmethod
    def _human_rate(cls, value):
        # Kept deliberately compact (<=6 chars) so the label gutter can
        # stay narrow: no decimal once the number reaches 3 digits, and
        # single-letter unit prefixes (K/M/G/T) instead of KB/MB/etc.
        for unit in cls._UNITS:
            if value < 1024 or unit == cls._UNITS[-1]:
                if unit == "B/s" or value >= 100:
                    return f"{value:.0f}{unit}"
                return f"{value:.1f}{unit}"
            value /= 1024
        return f"{value:.0f}{cls._UNITS[-1]}"

    @classmethod
    def _column_cells(cls, value, max_value, rows, mirrored):
        total_dots = rows * 4
        if max_value <= 0:
            filled = 0
        else:
            ratio = max(0.0, min(1.0, value / max_value))
            filled = round(ratio * total_dots)

        cells = [None] * rows
        remaining = filled
        row_order = range(rows) if mirrored else range(rows - 1, -1, -1)

        for r in row_order:
            n = min(4, remaining)
            remaining -= n
            cell = [False, False, False, False]
            if mirrored:
                # Baseline is at the top of this section; fill downward
                # from the top of each cell as the value grows.
                for k in range(n):
                    cell[k] = True
            else:
                # Baseline is at the bottom of this section; fill upward
                # from the bottom of each cell as the value grows.
                for k in range(4 - n, 4):
                    cell[k] = True
            cells[r] = cell

        return cells

    @classmethod
    def _build_grid(cls, history, rows, width, max_value, mirrored):
        if rows <= 0 or width <= 0:
            return []

        samples = list(history)[-width * 2:]
        if len(samples) < width * 2:
            samples = [0] * (width * 2 - len(samples)) + samples

        row_chars = [[] for _ in range(rows)]

        for column in range(width):
            left_value = samples[column * 2]
            right_value = samples[column * 2 + 1]
            left_cells = cls._column_cells(left_value, max_value, rows, mirrored)
            right_cells = cls._column_cells(right_value, max_value, rows, mirrored)

            for r in range(rows):
                bits = 0
                left_cell = left_cells[r]
                right_cell = right_cells[r]
                for k in range(4):
                    if left_cell[k]:
                        bits |= _DOT_BITS[k][0]
                    if right_cell[k]:
                        bits |= _DOT_BITS[k][1]
                row_chars[r].append(chr(_BRAILLE_BASE + bits))

        return ["".join(chars) for chars in row_chars]

    def _draw_label(self, x, y, gutter_width, text, color, align):
        text = text[-gutter_width:] if align == "right" else text[:gutter_width]
        if align == "right":
            start_x = x + max(0, gutter_width - len(text))
        else:
            start_x = x
        self.renderer.draw(start_x, y, text, color)

    def draw_content(self, x, y, width, height):
        if width <= 0 or height <= 0:
            return

        if self.error:
            self.renderer.draw(x, y, self.error[:width], self.colors.body)
            return

        left_gutter = min(self.LABEL_WIDTH, max(0, width - 1))
        graph_width = max(1, width - left_gutter)
        graph_x = x + left_gutter

        top_rows = height // 2
        bottom_rows = height - top_rows

        max_value = max(
            max(self.dl_history, default=0),
            max(self.ul_history, default=0),
            self.MIN_SCALE,
        )

        row = 0

        if top_rows > 0:
            lines = self._build_grid(
                self.dl_history, top_rows, graph_width, max_value, mirrored=False
            )
            for i, line in enumerate(lines):
                self.renderer.draw(graph_x, y + row + i, line, self.download_color)

            # Download label sits on the left, on the row nearest the
            # centerline, directly above the upload label below.
            if left_gutter > 0:
                label_row = y + row + top_rows - 1
                down_str = f"\u2193{self._human_rate(self.download_rate)}"
                self._draw_label(
                    x, label_row, left_gutter, down_str, self.download_color, "right"
                )
            row += top_rows

        if bottom_rows > 0:
            lines = self._build_grid(
                self.ul_history, bottom_rows, graph_width, max_value, mirrored=True
            )
            for i, line in enumerate(lines):
                self.renderer.draw(graph_x, y + row + i, line, self.upload_color)

            # Upload label sits on the left too, directly beneath the
            # download label, both stacked at the centerline.
            if left_gutter > 0:
                label_row = y + row
                up_str = f"\u2191{self._human_rate(self.upload_rate)}"
                self._draw_label(
                    x, label_row, left_gutter, up_str, self.upload_color, "right"
                )