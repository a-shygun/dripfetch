from dataclasses import dataclass


@dataclass(frozen=True)
class RGBA:
    r: int
    g: int
    b: int
    a: int


class BoxColors:
    def __init__(self, config, overrides=None):
        self.config = config
        self.overrides = overrides or {}
        self.boxes = config.get("boxes", {})
        self.custom = self.overrides.get("colors", {})

        self.border = self._resolve(
            "border_color",
            "#FFFFFFFF",
        )

        self.text = self._resolve(
            "text_color",
            "#FFFFFFFF",
        )

        self.accent = self._resolve(
            "accent_color",
            "#FFFFFFFF",
        )

        self.background = self._parse(
            config.get("background", "#00000000"),
        )

        self.title = self._custom("title", self.accent)
        self.line = self._custom("line", self.accent)
        self.body = self._custom("text", self.text)

    def _resolve(self, key, default):
        return self._parse(
            self.overrides.get(
                key,
                self.boxes.get(key, default),
            )
        )

    def _custom(self, key, default):
        if not isinstance(self.custom, dict):
            return default

        value = self.custom.get(key)

        return self._parse(value) if value is not None else default

    @staticmethod
    def _parse(value):
        if not isinstance(value, str) or not value.startswith("#"):
            raise ValueError(f"Invalid color: {value}")

        value = value[1:]

        if len(value) == 6:
            value += "FF"
        elif len(value) != 8:
            raise ValueError(f"Invalid color: #{value}")

        try:
            return RGBA(
                int(value[0:2], 16),
                int(value[2:4], 16),
                int(value[4:6], 16),
                int(value[6:8], 16),
            )
        except ValueError as exc:
            raise ValueError(f"Invalid color: #{value}") from exc

    @property
    def border_attr(self):
        return self.border

    @property
    def text_attr(self):
        return self.text

    @property
    def accent_attr(self):
        return self.accent

    @property
    def title_attr(self):
        return self.title

    @property
    def line_attr(self):
        return self.line

    @property
    def body_attr(self):
        return self.body

    @property
    def fill_attr(self):
        return self.background

    @property
    def background_enabled(self):
        return self.background.a > 0