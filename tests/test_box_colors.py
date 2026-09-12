from dripfetch.box.manager import BoxColors
from dripfetch.app.terminal import RGBA


def test_default_colors():
    config = {}

    colors = BoxColors(config)

    assert colors.border == RGBA(255, 255, 255, 255)
    assert colors.text == RGBA(255, 255, 255, 255)
    assert colors.accent == RGBA(255, 255, 255, 255)
    assert colors.background == RGBA(0, 0, 0, 0)


def test_global_box_colors():
    config = {
        "background": "#10203040",
        "boxes": {
            "border_color": "#FF0000",
            "text_color": "#00FF00",
            "accent_color": "#0000FF",
        },
    }

    colors = BoxColors(config)

    assert colors.border == RGBA(255, 0, 0, 255)
    assert colors.text == RGBA(0, 255, 0, 255)
    assert colors.accent == RGBA(0, 0, 255, 255)
    assert colors.background == RGBA(16, 32, 48, 64)


def test_box_overrides():
    config = {
        "boxes": {
            "border_color": "#FF0000",
            "text_color": "#00FF00",
            "accent_color": "#0000FF",
        },
    }

    overrides = {
        "border_color": "#111111",
        "text_color": "#222222",
        "accent_color": "#333333",
    }

    colors = BoxColors(config, overrides)

    assert colors.border == RGBA(17, 17, 17)
    assert colors.text == RGBA(34, 34, 34)
    assert colors.accent == RGBA(51, 51, 51)


def test_custom_colors():
    config = {
        "boxes": {
            "accent_color": "#123456",
        },
    }

    overrides = {
        "colors": {
            "title": "#FF0000",
            "line": "#00FF00",
            "text": "#0000FF",
        },
    }

    colors = BoxColors(config, overrides)

    assert colors.title == RGBA(255, 0, 0)
    assert colors.line == RGBA(0, 255, 0)
    assert colors.body == RGBA(0, 0, 255)


def test_custom_colors_fall_back_to_defaults():
    config = {
        "boxes": {
            "accent_color": "#123456",
            "text_color": "#654321",
        },
    }

    colors = BoxColors(config)

    assert colors.title == colors.accent
    assert colors.line == colors.accent
    assert colors.body == colors.text


def test_background_enabled():
    assert BoxColors(
        {"background": "#000000FF"}
    ).background_enabled


def test_background_disabled():
    assert not BoxColors(
        {"background": "#00000000"}
    ).background_enabled