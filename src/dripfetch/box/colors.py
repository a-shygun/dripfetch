from ..app.terminal import parse_color


class BoxColors:
    def __init__(self, config):
        box_config = config.get("boxes", {})
        self.border = parse_color(box_config.get("border_color", "#FFFFFFFF"))
        self.text = parse_color(box_config.get("text_color", "#FFFFFFFF"))
        self.accent = parse_color(box_config.get("accent_color", "#FFFFFFFF"))
        # Matches the default the Renderer fills the screen with in
        # app.py (config.get("background", "#000000FF")). These two must
        # stay in sync: if a config omits "background" entirely, the
        # canvas is opaque black, so background_enabled below should be
        # True to match, not False.
        self.background = parse_color(config.get("background", "#000000FF"))
        self.title = self.accent
        self.line = self.accent
        self.body = self.text

    @property
    def background_enabled(self):
        return self.background.a > 0
