from ..base import BaseBox


class TextBox(BaseBox):
    ALIGNMENT = "center"
    ALIGNMENTS = {"left", "center", "right"}

    # ------------------------------------------------------------------
    # Plug-and-play config validator (called by config.py automatically)
    # ------------------------------------------------------------------
    @classmethod
    def validate_config(cls, item, path):
        from ...app.config import _enum, _error, _string  # noqa: PLC0415

        if "alignment" in item:
            _enum(item["alignment"], f"{path}.alignment", cls.ALIGNMENTS)
        if "text" in item:
            text = item["text"]
            text_path = f"{path}.text"
            if isinstance(text, str):
                return
            if not isinstance(text, list):
                _error(text_path, "must be a string or list of strings")
            for index, line in enumerate(text):
                _string(line, f"{text_path}[{index}]")

    def __init__(self, stdscr, config, box_config, colors, renderer):
        super().__init__(stdscr, config, box_config, colors, renderer)
        self.ALIGNMENT = config.get("alignment", self.ALIGNMENT)

    def content(self):
        text = self.config.get("text", "")
        lines = text if isinstance(text, list) else text.splitlines()
        # Plain strings render with foreground=None, which Renderer.draw
        # treats as "terminal default" rather than any configured color
        # -- so without this, text_color in config.yaml was silently
        # ignored. Pair each line with the box's text color explicitly,
        # same as every other box type (weather, calendar, net, etc.)
        # already does via self.colors.body/title/line.
        return [[(line, self.colors.body)] for line in lines]