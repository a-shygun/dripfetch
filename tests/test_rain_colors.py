import pytest

from dripfetch.rain.colors import ColorManager, RGBA, get_rgb


def test_get_rgb_six_digit():
    assert get_rgb("#12ABEF") == RGBA(18, 171, 239, 255)


def test_get_rgb_eight_digit():
    assert get_rgb("#12ABEF80") == RGBA(18, 171, 239, 128)


def test_get_rgb_without_hash():
    assert get_rgb("12ABEF") == RGBA(18, 171, 239, 255)


@pytest.mark.parametrize(
    "value",
    ["", "#", "#12345", "#1234567", "#GGGGGG", "#12345G"],
)
def test_get_rgb_invalid(value):
    with pytest.raises(ValueError):
        get_rgb(value)


def test_color_manager_create_pairs():
    manager = ColorManager()
    manager.create_pairs(["#FF0000", "#00FF00"])

    assert manager.colors["#FF0000"] == RGBA(255, 0, 0)
    assert manager.colors["#00FF00"] == RGBA(0, 255, 0)


def test_color_manager_attribute_head_is_full_brightness():
    manager = ColorManager()
    manager.create_pairs(["#FF0000"])

    assert manager.attribute("#FF0000", 0, 5) == RGBA(255, 0, 0)


def test_color_manager_attribute_tail_fades():
    manager = ColorManager()
    manager.create_pairs(["#FF0000"])

    assert manager.attribute("#FF0000", 4, 5) == RGBA(0, 0, 0)


def test_color_manager_attribute_middle_brightness():
    manager = ColorManager()
    manager.create_pairs(["#FFFFFF"])

    assert manager.attribute("#FFFFFF", 2, 5) == RGBA(128, 128, 128)


def test_color_manager_attribute_single_length():
    manager = ColorManager()
    manager.create_pairs(["#FFFFFF"])

    assert manager.attribute("#FFFFFF", 0, 1) == RGBA(255, 255, 255)


def test_color_manager_unknown_color_defaults_to_white():
    manager = ColorManager()

    assert manager.attribute("#UNKNOWN", 0, 1) == RGBA(255, 255, 255)
