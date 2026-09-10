from collections import deque

from dripfetch.rain.drop import Drop
from dripfetch.rain.movement import move_down, move_horizontal


def test_move_down():
    drop = Drop(x=5, head_y=2, path=deque(maxlen=5))

    move_down(drop, [], False, 80, "│")

    assert drop.head_y == 3
    assert drop.x == 5
    assert list(drop.path) == [(5, 3, "│")]


def test_move_down_appends_to_existing_path():
    drop = Drop(
        x=5,
        head_y=2,
        path=deque([(5, 2, "│")], maxlen=5),
    )

    move_down(drop, [], False, 80, "│")

    assert list(drop.path) == [
        (5, 2, "│"),
        (5, 3, "│"),
    ]


def test_move_down_collision_redirects():
    drop = Drop(
        x=15,
        head_y=4,
        path=deque([(15, 4, "│")], maxlen=5),
    )

    bounds = [(10, 5, 20, 10)]

    move_down(drop, bounds, True, 80, "│")

    assert drop.head_y == 4
    assert drop.redirect_target == 8
    assert drop.path[-1] == (15, 4, "┘")


def test_move_horizontal_moves_left():
    drop = Drop(
        x=15,
        head_y=4,
        redirect_target=10,
        path=deque(maxlen=5),
    )

    move_horizontal(drop)

    assert drop.x == 14
    assert drop.redirect_target == 10
    assert drop.path[-1] == (14, 4, "─")


def test_move_horizontal_moves_right():
    drop = Drop(
        x=15,
        head_y=4,
        redirect_target=20,
        path=deque(maxlen=5),
    )

    move_horizontal(drop)

    assert drop.x == 16
    assert drop.redirect_target == 20
    assert drop.path[-1] == (16, 4, "─")


def test_move_horizontal_finishes_right_redirect():
    drop = Drop(
        x=19,
        head_y=4,
        redirect_target=20,
        path=deque(maxlen=5),
    )

    move_horizontal(drop)

    assert drop.x == 20
    assert drop.redirect_target is None
    assert drop.path[-1] == (20, 4, "┐")


def test_move_horizontal_finishes_left_redirect():
    drop = Drop(
        x=11,
        head_y=4,
        redirect_target=10,
        path=deque(maxlen=5),
    )

    move_horizontal(drop)

    assert drop.x == 10
    assert drop.redirect_target is None
    assert drop.path[-1] == (10, 4, "┌")


def test_move_horizontal_without_target_does_nothing():
    drop = Drop(
        x=15,
        head_y=4,
        path=deque(maxlen=5),
    )

    move_horizontal(drop)

    assert drop.x == 15
    assert drop.head_y == 4
    assert not drop.path
