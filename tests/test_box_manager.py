from unittest.mock import Mock

import curses
import pytest

from dripfetch.box.manager import Border, Placement


def placement(layout="qwerty"):
    stdscr = Mock()
    stdscr.getmaxyx.return_value = (30, 100)
    return Placement(stdscr, layout)


@pytest.mark.parametrize(
    ("name", "characters", "visible"),
    [
        (
            "single",
            ("─", "│", "┌", "┐", "└", "┘"),
            True,
        ),
        (
            "double",
            ("═", "║", "╔", "╗", "╚", "╝"),
            True,
        ),
        (
            "none",
            ("", "", "", "", "", ""),
            False,
        ),
    ],
)
def test_border_types(name, characters, visible):
    border = Border(name)

    assert border.name == name
    assert border.characters == characters
    assert border.visible is visible


def test_unknown_border_falls_back_to_single():
    border = Border("invalid")

    assert border.name == "single"
    assert border.visible


def test_border_dimensions():
    border = Border("single")

    assert border.dimensions(20, 10, 2, 1) == (26, 14)


def test_placement_center():
    assert placement().center(20, 10) == [40, 10]


def test_placement_center_with_offset():
    assert placement().center(
        20,
        10,
        {"horizontal": 5, "vertical": -2},
    ) == [45, 8]


def test_placement_clamp():
    position = [90, 25]

    result = placement().clamp(position, 20, 10)

    assert result is None
    assert position == [80, 20]


def test_placement_clamp_negative():
    position = [-10, -5]

    placement().clamp(position, 20, 10)

    assert position == [0, 0]


def test_placement_clamp_oversized_box():
    position = [50, 20]

    placement().clamp(position, 120, 40)

    assert position == [0, 0]


def test_placement_relative():
    assert placement().relative([40, 10], 20, 10) == (0, 0)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (ord("w"), (0, -1)),
        (ord("a"), (-1, 0)),
        (ord("s"), (0, 1)),
        (ord("d"), (1, 0)),
        (curses.KEY_UP, (0, -1)),
        (curses.KEY_LEFT, (-1, 0)),
        (curses.KEY_DOWN, (0, 1)),
        (curses.KEY_RIGHT, (1, 0)),
    ],
)
def test_qwerty_movement(key, expected):
    assert placement()._movement()[key] == expected


def test_azerty_movement():
    result = placement("azerty")._movement()

    assert result[ord("z")] == (0, -1)
    assert result[ord("q")] == (-1, 0)
    assert result[ord("s")] == (0, 1)
    assert result[ord("d")] == (1, 0)


def test_qwertz_layout():
    result = placement("qwertz")._movement()

    assert result[ord("w")] == (0, -1)
    assert result[ord("a")] == (-1, 0)
    assert result[ord("s")] == (0, 1)
    assert result[ord("d")] == (1, 0)


def test_invalid_layout_falls_back_to_qwerty():
    assert placement("invalid").layout == "qwerty"


def test_non_string_layout_falls_back_to_qwerty():
    assert placement(None).layout == "qwerty"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (ord("w"), (0, -1)),
        (ord("a"), (-1, 0)),
        (ord("s"), (0, 1)),
        (ord("d"), (1, 0)),
        (curses.KEY_UP, (0, -1)),
        (curses.KEY_LEFT, (-1, 0)),
        (curses.KEY_DOWN, (0, 1)),
        (curses.KEY_RIGHT, (1, 0)),
    ],
)
def test_move(key, expected):
    position = [10, 10]

    assert placement().move(position, key)
    assert position == [
        10 + expected[0],
        10 + expected[1],
    ]


def test_move_unknown_key():
    position = [10, 10]

    assert not placement().move(position, ord("x"))
    assert position == [10, 10]