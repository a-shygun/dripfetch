from ..base import BaseBox
from .helper import validation


class TextBox(BaseBox):
    ALIGNMENT = "center"
    ALIGNMENTS = {"left", "center", "right"}

    def __init__(self, stdscr, config, box_config, colors, renderer):
        super().__init__(stdscr, config, box_config, colors, renderer)
        self.ALIGNMENT = config.get("alignment", self.ALIGNMENT)

    @classmethod
    def validate_config(cls, item, path):
        if "alignment" in item:
            validation.enum(item["alignment"], f"{path}.alignment", cls.ALIGNMENTS)
        if "text" in item:
            text = item["text"]
            text_path = f"{path}.text"
            if isinstance(text, str):
                return
            if not isinstance(text, list):
                validation.error(text_path, "must be a string or list of strings")
            for index, line in enumerate(text):
                validation.string(line, f"{text_path}[{index}]")

    def content(self):
        text = self.config.get("text", "")
        lines = text if isinstance(text, list) else text.splitlines()
        # Pair each line with the box's text color explicitly: plain strings
        # render with foreground=None, which Renderer.draw treats as
        # "terminal default", so text_color would be silently ignored.
        return [[(line, self.colors.body)] for line in lines]
