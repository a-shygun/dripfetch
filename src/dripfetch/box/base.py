class BaseBox:
    def __init__(self, stdscr, config, boxes, colors, renderer=None):
        self.stdscr = stdscr
        self.config = config
        self.boxes = boxes
        self.colors = colors
        self.renderer = renderer

    @property
    def padding(self):
        padding = self.boxes.get("padding", {})
        return padding.get("horizontal", 2), padding.get("vertical", 1)

    def update(self):
        pass

    def dimensions(self):
        raise NotImplementedError

    def draw_content(self, x, y, width, height):
        raise NotImplementedError

    def close(self):
        pass
