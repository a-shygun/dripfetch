from ..base import BaseBox
from .helper import validation
from .helper.braille import build_grid
from .helper.net_sampler import NetSampler
from .helper.parsing import clamp_float, clamp_int, color_or_default
from .helper.units import human_rate


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
    # rate labels, e.g. "\u2193999K/s".
    LABEL_WIDTH = 8

    def __init__(self, stdscr, config, boxes, colors, renderer):
        super().__init__(stdscr, config, boxes, colors, renderer)

        self.width = clamp_int(
            config.get("width", self.DEFAULT_WIDTH), self.MIN_WIDTH
        )
        self.height = clamp_int(
            config.get("height", self.DEFAULT_HEIGHT), self.MIN_HEIGHT
        )
        interval = clamp_float(
            config.get("interval", self.DEFAULT_INTERVAL),
            self.MIN_INTERVAL,
            self.DEFAULT_INTERVAL,
        )

        self.download_color = color_or_default(config.get("download_color"), colors.body)
        self.upload_color = color_or_default(config.get("upload_color"), colors.body)

        # Two samples of history are consumed per character column (one
        # per braille dot-column), so keep 2x the graph width buffered.
        self.sampler = NetSampler(self.width * 2, interval)

    @classmethod
    def validate_config(cls, item, path):
        if "width" in item:
            validation.integer(item["width"], f"{path}.width")
        if "height" in item:
            validation.integer(item["height"], f"{path}.height")
        if "interval" in item:
            validation.number(item["interval"], f"{path}.interval")
        if "download_color" in item:
            validation.string(item["download_color"], f"{path}.download_color")
        if "upload_color" in item:
            validation.string(item["upload_color"], f"{path}.upload_color")

    # ------------------------------------------------------------------
    # BaseBox interface
    # ------------------------------------------------------------------
    def dimensions(self):
        return self.width + self.LABEL_WIDTH, self.height

    def update(self):
        self.sampler.update()

    def draw_content(self, x, y, width, height):
        if width <= 0 or height <= 0:
            return

        sampler = self.sampler

        if sampler.error:
            self.renderer.draw(x, y, sampler.error[:width], self.colors.body)
            return

        left_gutter = min(self.LABEL_WIDTH, max(0, width - 1))
        graph_width = max(1, width - left_gutter)
        graph_x = x + left_gutter

        top_rows = height // 2
        bottom_rows = height - top_rows
        max_value = max(sampler.peak, self.MIN_SCALE)

        if top_rows > 0:
            self._draw_graph(
                graph_x, y, top_rows, graph_width,
                sampler.download_history, max_value, False, self.download_color,
            )
            # Download label sits on the row nearest the centerline,
            # directly above the upload label below.
            self._draw_label(
                x, y + top_rows - 1, left_gutter,
                f"\u2193{human_rate(sampler.download_rate)}", self.download_color,
            )

        if bottom_rows > 0:
            row = y + top_rows
            self._draw_graph(
                graph_x, row, bottom_rows, graph_width,
                sampler.upload_history, max_value, True, self.upload_color,
            )
            self._draw_label(
                x, row, left_gutter,
                f"\u2191{human_rate(sampler.upload_rate)}", self.upload_color,
            )

    # ------------------------------------------------------------------
    # Drawing pieces
    # ------------------------------------------------------------------
    def _draw_graph(self, x, y, rows, width, history, max_value, mirrored, color):
        lines = build_grid(history, rows, width, max_value, mirrored)
        for offset, line in enumerate(lines):
            self.renderer.draw(x, y + offset, line, color)

    def _draw_label(self, x, y, gutter_width, text, color):
        """Right-aligned label inside the left gutter."""
        if gutter_width <= 0:
            return
        text = text[-gutter_width:]
        self.renderer.draw(x + max(0, gutter_width - len(text)), y, text, color)
