from unittest.mock import Mock

from dripfetch.box.placement import Placement


def placement():
    stdscr = Mock()
    stdscr.getmaxyx.return_value = (30, 100)
    return Placement(stdscr)


def test_center():
    assert placement().center(20, 10) == [40, 10]


def test_center_with_offset():
    assert placement().center(
        20,
        10,
        {"horizontal": 5, "vertical": -2},
    ) == [45, 8]


def test_clamp():
    position = [90, 25]

    result = placement().clamp(position, 20, 10)

    assert result == [80, 20]
    assert position == [80, 20]


def test_clamp_negative():
    position = [-10, -5]

    result = placement().clamp(position, 20, 10)

    assert result == [0, 0]
    assert position == [0, 0]


def test_clamp_oversized_box():
    position = [50, 20]

    result = placement().clamp(position, 120, 40)

    assert result == [0, 0]


def test_relative():
    assert placement().relative([40, 10], 20, 10) == (0, 0)
