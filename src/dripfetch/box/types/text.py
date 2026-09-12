from ..manager import BaseBox


class TextBox(BaseBox):
    ALIGNMENT = "center"

    def content(self):
        return str(
            self.config.get("text", "")
        ).splitlines()