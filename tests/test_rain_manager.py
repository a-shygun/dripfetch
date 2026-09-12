from collections import deque
from unittest.mock import Mock

import pytest

from dripfetch.app.terminal import RGBA
from dripfetch.rain.manager import (
    BOX_PADDING,
    ColorManager,
    Drop,
    Rain,
)


BOUNDS = [
    (10, 5, 20, 10),
    (30, 15, 40, 20),
]


def rain(config=None, width=80, height=30):
    stdscr = Mock()
    stdscr.getmaxyx.return_value = (height, width)

    box = Mock()
    renderer = Mock()

    return Rain(
        stdscr,
        config or {},
        box,
        renderer,
    )


# ---------------------------------------------------------------------------
# Drop
# ---------------------------------------------------------------------------


def test_drop_defaults():
    drop = Drop(x=5)

    assert drop.x == 5
    assert drop.head_y == -1
    assert drop.speed == 50
    assert drop.length == 5
    assert drop.color == "#FFFFFF"
    assert drop.character == "│"
    assert isinstance(drop.path, deque)
    assert drop.redirect_target is None
    assert drop.active


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------


def test_color_manager_create_pairs():
    manager = ColorManager()

    manager.create_pairs([
        "#FF0000",
        "#00FF00",
    ])

    assert manager.colors["#FF0000"] == RGBA(255, 0, 0)
    assert manager.colors["#00FF00"] == RGBA(0, 255, 0)


def test_color_manager_head_is_full_brightness():
    manager = ColorManager()
    manager.create_pairs(["#FF0000"])

    assert manager.attribute(
        "#FF0000",
        0,
        5,
    ) == RGBA(255, 0, 0)


def test_color_manager_tail_fades():
    manager = ColorManager()
    manager.create_pairs(["#FF0000"])

    assert manager.attribute(
        "#FF0000",
        4,
        5,
    ) == RGBA(0, 0, 0)


def test_color_manager_middle_brightness():
    manager = ColorManager()
    manager.create_pairs(["#FFFFFF"])

    assert manager.attribute(
        "#FFFFFF",
        2,
        5,
    ) == RGBA(128, 128, 128)


def test_color_manager_single_length():
    manager = ColorManager()
    manager.create_pairs(["#FFFFFF"])

    assert manager.attribute(
        "#FFFFFF",
        0,
        1,
    ) == RGBA(255, 255, 255)


def test_color_manager_unknown_color_is_white():
    manager = ColorManager()

    assert manager.attribute(
        "#UNKNOWN",
        0,
        1,
    ) == RGBA(255, 255, 255)


# ---------------------------------------------------------------------------
# Collision
# ---------------------------------------------------------------------------


def test_collision_disabled():
    rain_instance = rain({
        "rain": {
            "collision": False,
        },
    })

    assert rain_instance._collision(
        15,
        4,
        5,
        BOUNDS,
    ) is None


def test_collision_detects_top_edge():
    rain_instance = rain()

    assert rain_instance._collision(
        15,
        4,
        5,
        BOUNDS,
    ) == (8, 5)


def test_collision_redirects_to_nearest_side():
    rain_instance = rain()

    assert rain_instance._collision(
        19,
        4,
        5,
        BOUNDS,
    ) == (22, 5)


def test_collision_clamps_left_target():
    rain_instance = rain(width=20)

    assert rain_instance._collision(
        1,
        4,
        5,
        [(0, 5, 10, 10)],
    ) == (0, 5)


def test_collision_clamps_right_target():
    rain_instance = rain(width=21)

    assert rain_instance._collision(
        18,
        4,
        5,
        [(10, 5, 20, 10)],
    ) == (20, 5)


def test_collision_requires_crossing_top_edge():
    rain_instance = rain()

    assert rain_instance._collision(
        15,
        5,
        6,
        BOUNDS,
    ) is None


def test_collision_requires_same_x_inside_box():
    rain_instance = rain()

    assert rain_instance._collision(
        25,
        4,
        5,
        BOUNDS,
    ) is None


def test_collision_uses_expected_padding():
    rain_instance = rain()

    result = rain_instance._collision(
        15,
        4,
        5,
        BOUNDS,
    )

    assert result[0] in {
        10 - BOX_PADDING,
        20 + BOX_PADDING,
    }


def test_inside_box_true():
    rain_instance = rain()

    assert rain_instance._inside_box(
        15,
        7,
        BOUNDS,
    )


def test_inside_box_on_boundary():
    rain_instance = rain()

    assert rain_instance._inside_box(
        10,
        5,
        BOUNDS,
    )

    assert rain_instance._inside_box(
        20,
        10,
        BOUNDS,
    )


def test_inside_box_false():
    rain_instance = rain()

    assert not rain_instance._inside_box(
        25,
        7,
        BOUNDS,
    )

    assert not rain_instance._inside_box(
        15,
        12,
        BOUNDS,
    )


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------


def test_move_down():
    rain_instance = rain()

    drop = Drop(
        x=5,
        head_y=2,
        path=deque(maxlen=5),
    )

    rain_instance._move_down(drop, [])

    assert drop.head_y == 3
    assert drop.x == 5
    assert list(drop.path) == [
        (5, 3, "│"),
    ]


def test_move_down_appends_to_existing_path():
    rain_instance = rain()

    drop = Drop(
        x=5,
        head_y=2,
        path=deque(
            [(5, 2, "│")],
            maxlen=5,
        ),
    )

    rain_instance._move_down(drop, [])

    assert list(drop.path) == [
        (5, 2, "│"),
        (5, 3, "│"),
    ]


def test_move_down_collision_redirects():
    rain_instance = rain()

    drop = Drop(
        x=15,
        head_y=4,
        path=deque(
            [(15, 4, "│")],
            maxlen=5,
        ),
    )

    rain_instance._move_down(
        drop,
        [(10, 5, 20, 10)],
    )

    assert drop.head_y == 4
    assert drop.redirect_target == 8
    assert drop.path[-1] == (
        15,
        4,
        "┘",
    )


def test_move_horizontal_moves_left():
    rain_instance = rain()

    drop = Drop(
        x=15,
        head_y=4,
        redirect_target=10,
        path=deque(maxlen=5),
    )

    rain_instance._move_horizontal(drop)

    assert drop.x == 14
    assert drop.redirect_target == 10
    assert drop.path[-1] == (
        14,
        4,
        "─",
    )


def test_move_horizontal_moves_right():
    rain_instance = rain()

    drop = Drop(
        x=15,
        head_y=4,
        redirect_target=20,
        path=deque(maxlen=5),
    )

    rain_instance._move_horizontal(drop)

    assert drop.x == 16
    assert drop.redirect_target == 20
    assert drop.path[-1] == (
        16,
        4,
        "─",
    )


def test_move_horizontal_finishes_right_redirect():
    rain_instance = rain()

    drop = Drop(
        x=19,
        head_y=4,
        redirect_target=20,
        path=deque(maxlen=5),
    )

    rain_instance._move_horizontal(drop)

    assert drop.x == 20
    assert drop.redirect_target is None
    assert drop.path[-1] == (
        20,
        4,
        "┐",
    )


def test_move_horizontal_finishes_left_redirect():
    rain_instance = rain()

    drop = Drop(
        x=11,
        head_y=4,
        redirect_target=10,
        path=deque(maxlen=5),
    )

    rain_instance._move_horizontal(drop)

    assert drop.x == 10
    assert drop.redirect_target is None
    assert drop.path[-1] == (
        10,
        4,
        "┌",
    )


def test_move_horizontal_without_target_does_nothing():
    rain_instance = rain()

    drop = Drop(
        x=15,
        head_y=4,
        path=deque(maxlen=5),
    )

    rain_instance._move_horizontal(drop)

    assert drop.x == 15
    assert drop.head_y == 4
    assert not drop.path


# ---------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------


def test_choose_empty_returns_default():
    assert Rain._choose([], 42) == 42


def test_choose_single_value():
    assert Rain._choose(
        [(1, 42)],
        0,
    ) == 42


def test_choose_respects_available_values():
    values = [
        (1, "a"),
        (1, "b"),
        (1, "c"),
    ]

    for _ in range(100):
        assert Rain._choose(
            values,
            "x",
        ) in {"a", "b", "c"}


def test_choose_character_string():
    assert Rain._choose_character("│") == "│"


def test_choose_character_empty_list():
    assert Rain._choose_character([]) == "│"


def test_choose_character_list():
    characters = ["│", "|", "┃"]

    for _ in range(100):
        assert Rain._choose_character(
            characters
        ) in characters


def test_new_drop():
    rain_instance = rain({
        "rain": {
            "speeds": [(1, 50)],
            "lengths": [(1, 5)],
            "colors": [(1, "#FFFFFF")],
        },
    })

    drop = rain_instance._new_drop()

    assert isinstance(drop, Drop)
    assert 0 <= drop.x < 80
    assert drop.head_y == -1
    assert drop.speed == 50
    assert drop.length == 5
    assert drop.color == "#FFFFFF"
    assert isinstance(drop.path, deque)
    assert drop.path.maxlen == 5
    assert drop.active


def test_new_drop_invalid_width():
    rain_instance = rain(width=0)

    assert rain_instance._new_drop() is None


def test_new_drop_minimum_length():
    rain_instance = rain({
        "rain": {
            "lengths": [(1, 0)],
        },
    })

    drop = rain_instance._new_drop()

    assert drop.length == 1


def test_new_drop_minimum_speed():
    rain_instance = rain({
        "rain": {
            "speeds": [(1, 0)],
        },
    })

    drop = rain_instance._new_drop()

    assert drop.speed == 1


def test_spawn_disabled():
    rain_instance = rain({
        "rain": {
            "intensity": 0,
        },
    })

    rain_instance.spawned_at = 100.0
    rain_instance._spawn(101.0)

    assert rain_instance.spawned == 0
    assert rain_instance.spawned_at == 101.0
    assert not rain_instance.drops


def test_spawn_creates_drops(monkeypatch):
    rain_instance = rain({
        "rain": {
            "intensity": 20,
            "speeds": [(1, 50)],
            "lengths": [(1, 5)],
            "colors": [(1, "#FFFFFF")],
        },
    })

    rain_instance.spawned_at = 100.0

    rain_instance._spawn(100.25)

    assert len(rain_instance.drops) == 1
    assert rain_instance.spawned == pytest.approx(0.0)
    assert rain_instance.spawned_at == 100.25


def test_spawn_preserves_fractional_drops():
    rain_instance = rain({
        "rain": {
            "intensity": 1,
        },
    })

    rain_instance.spawned_at = 100.0

    rain_instance._spawn(101.0)

    assert rain_instance.spawned == pytest.approx(0.05)
    assert not rain_instance.drops


def test_spawn_caps_elapsed_time():
    rain_instance = rain({
        "rain": {
            "intensity": 100,
            "speeds": [(1, 50)],
            "lengths": [(1, 5)],
            "colors": [(1, "#FFFFFF")],
        },
    })

    rain_instance.spawned_at = 100.0

    rain_instance._spawn(110.0)

    assert len(rain_instance.drops) == 5