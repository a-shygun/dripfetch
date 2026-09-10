import pytest

from dripfetch.box.borders import Border


@pytest.mark.parametrize(
    "style",
    ["single", "double", "rounded", "none"],
)
def test_border_can_be_created(style):
    border = Border(style)

    assert border is not None


def test_unknown_border_falls_back_or_raises():
    try:
        border = Border("invalid")
    except ValueError:
        return

    assert border is not None
