class BaseBox:
    ALIGNMENT = "left"

    def __init__(
        self,
        stdscr,
        config,
        box_config,
        colors,
        renderer,
    ):
        self.stdscr = stdscr
        self.config = config
        self.box_config = box_config
        self.colors = colors
        self.renderer = renderer

        # content() can be expensive (parsing ASCII art, re-locking and
        # copying shared state, formatting colored segments, ...), and
        # without caching it was being called up to three times per
        # frame at ~100 frames/sec: once from dimensions(), again from
        # draw_content(), and again whenever BoxManager checks box sizes
        # -- even for boxes whose content hadn't changed at all between
        # those calls. Subclasses that mutate their own data (sysinfo,
        # weather, ...) call mark_dirty() when that happens; boxes whose
        # content never changes after construction (logo, text) simply
        # never call it again, so it's computed once and reused forever.
        self._content_cache = None
        self._content_dirty = True

    @property
    def padding(self):
        padding = self.box_config.get("padding", {})
        return (
            padding.get("horizontal", 2),
            padding.get("vertical", 1),
        )

    def content(self):
        return []

    def mark_dirty(self):
        """Invalidate the cached content() result. Call this whenever the
        data content() depends on changes; otherwise dimensions() and
        draw_content() will keep serving the stale cached version."""
        self._content_dirty = True

    def _cached_content(self):
        if self._content_dirty or self._content_cache is None:
            self._content_cache = self.content()
            self._content_dirty = False
        return self._content_cache

    def update(self):
        pass

    def dimensions(self):
        lines = self._cached_content()
        width = max(
            (self._line_width(line) for line in lines),
            default=0,
        )
        return width, len(lines)

    def draw_content(self, x, y, width, height):
        lines = self._cached_content()
        for row, line in enumerate(lines[:height]):
            segments = self._segments(line)
            line_width = self._line_width(segments)
            if self.ALIGNMENT == "center":
                column = x + max(
                    0,
                    (width - line_width) // 2,
                )
            elif self.ALIGNMENT == "right":
                column = x + max(
                    0,
                    width - line_width,
                )
            else:
                column = x
            for text, color in segments:
                if column >= x + width:
                    break
                available = x + width - column
                text = text[:available]
                if text:
                    self.renderer.draw(
                        column,
                        y + row,
                        text,
                        color,
                    )
                column += len(text)

    def close(self):
        pass

    @staticmethod
    def _segments(line):
        if isinstance(line, str):
            return [(line, None)]
        return line

    @classmethod
    def _line_width(cls, line):
        return sum(len(text) for text, _ in cls._segments(line))
