from dripfetch.rain.collision import BOX_PADDING, collision, inside_box


BOUNDS = [
    (10, 5, 20, 10),
    (30, 15, 40, 20),
]


def test_collision_disabled():
    assert collision(15, 4, 5, BOUNDS, False, 80) is None


def test_collision_detects_top_edge():
    assert collision(15, 4, 5, BOUNDS, True, 80) == (8, 5)


def test_collision_redirects_to_nearest_side():
    assert collision(19, 4, 5, BOUNDS, True, 80) == (22, 5)


def test_collision_clamps_left_target():
    assert collision(1, 4, 5, [(0, 5, 10, 10)], True, 20) == (
        0,
        5,
    )


def test_collision_clamps_right_target():
    assert collision(18, 4, 5, [(10, 5, 20, 10)], True, 21) == (
        20,
        5,
    )


def test_collision_requires_crossing_top_edge():
    assert collision(15, 5, 6, BOUNDS, True, 80) is None


def test_collision_requires_same_x_inside_box():
    assert collision(25, 4, 5, BOUNDS, True, 80) is None


def test_collision_uses_expected_padding():
    result = collision(15, 4, 5, BOUNDS, True, 80)

    assert result[0] in {
        10 - BOX_PADDING,
        20 + BOX_PADDING,
    }


def test_inside_box_true():
    assert inside_box(15, 7, BOUNDS)


def test_inside_box_on_boundary():
    assert inside_box(10, 5, BOUNDS)
    assert inside_box(20, 10, BOUNDS)


def test_inside_box_false():
    assert not inside_box(25, 7, BOUNDS)
    assert not inside_box(15, 12, BOUNDS)
