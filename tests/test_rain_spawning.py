from collections import deque

import pytest

from dripfetch.rain.drop import Drop
from dripfetch.rain.spawning import choose, new_drop, spawn


def test_choose_empty_returns_default():
    assert choose([], 42) == 42


def test_choose_single_value():
    assert choose([(1, 42)], 0) == 42


def test_choose_respects_available_values():
    values = [(1, "a"), (1, "b"), (1, "c")]

    for _ in range(100):
        assert choose(values, "x") in {"a", "b", "c"}


def test_new_drop():
    drop = new_drop(
        80,
        [(1, 50)],
        [(1, 5)],
        [(1, "#FFFFFF")],
    )

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
    assert new_drop(0, [], [], []) is None
    assert new_drop(-1, [], [], []) is None


def test_new_drop_minimum_length():
    drop = new_drop(
        80,
        [(1, 50)],
        [(1, 0)],
        [(1, "#FFFFFF")],
    )

    assert drop.length == 1


def test_new_drop_minimum_speed():
    drop = new_drop(
        80,
        [(1, 0)],
        [(1, 5)],
        [(1, "#FFFFFF")],
    )

    assert drop.speed == 1


def test_spawn_disabled():
    drops = []

    spawned, spawned_at = spawn(
        drops,
        80,
        0,
        0,
        100.0,
        101.0,
        [],
        [],
        [],
    )

    assert spawned == 0
    assert spawned_at == 101.0
    assert not drops


def test_spawn_creates_drops():
    drops = []

    spawned, spawned_at = spawn(
        drops,
        80,
        20,
        0,
        100.0,
        100.25,
        [(1, 50)],
        [(1, 5)],
        [(1, "#FFFFFF")],
    )

    assert len(drops) == 1
    assert spawned == pytest.approx(0.0)
    assert spawned_at == 100.25


def test_spawn_preserves_fractional_drops():
    drops = []

    spawned, _ = spawn(
        drops,
        80,
        1,
        0,
        100.0,
        101.0,
        [(1, 50)],
        [(1, 5)],
        [(1, "#FFFFFF")],
    )

    assert spawned == pytest.approx(0.05)
    assert not drops


def test_spawn_caps_elapsed_time():
    drops = []

    spawned, _ = spawn(
        drops,
        80,
        100,
        0,
        100.0,
        110.0,
        [(1, 50)],
        [(1, 5)],
        [(1, "#FFFFFF")],
    )

    assert len(drops) == 5
