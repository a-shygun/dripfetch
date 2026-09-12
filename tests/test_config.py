from pathlib import Path

import pytest

from dripfetch.app.config import (
    ConfigError,
    load_config,
    save_config,
    validate_config,
)


def test_validate_empty_config():
    config = validate_config({})

    assert config == {}


def test_validate_background():
    config = {
        "background": "#123456",
    }

    assert validate_config(config) == config


@pytest.mark.parametrize(
    "value",
    [
        "",
        "#",
        "#12345",
        "#1234567",
        "#GGGGGG",
        "#12345G",
    ],
)
def test_invalid_background_color(value):
    with pytest.raises(ConfigError):
        validate_config({
            "background": value,
        })


def test_valid_background_with_alpha():
    config = {
        "background": "#12345678",
    }

    assert validate_config(config) == config


def test_rain_collision_must_be_boolean():
    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "collision": "true",
            },
        })


def test_rain_intensity_must_be_non_negative_integer():
    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "intensity": -1,
            },
        })

    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "intensity": 1.5,
            },
        })


def test_rain_intensity_accepts_zero():
    config = {
        "rain": {
            "intensity": 0,
        },
    }

    assert validate_config(config) == config


def test_rain_character_accepts_string():
    config = {
        "rain": {
            "character": "│",
        },
    }

    assert validate_config(config) == config


def test_rain_character_accepts_list():
    config = {
        "rain": {
            "character": [
                "│",
                "|",
            ],
        },
    }

    assert validate_config(config) == config


def test_empty_rain_character_is_invalid():
    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "character": "",
            },
        })


def test_weighted_colors_must_sum_to_one():
    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "colors": [
                    [0.5, "#FFFFFF"],
                ],
            },
        })


def test_weighted_colors_are_valid():
    config = {
        "rain": {
            "colors": [
                [0.5, "#FFFFFF"],
                [0.5, "#000000"],
            ],
        },
    }

    assert validate_config(config) == config


def test_weighted_values_reject_zero_weight():
    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "speeds": [
                    [0, 50],
                    [1, 100],
                ],
            },
        })


def test_weighted_values_require_non_empty_list():
    with pytest.raises(ConfigError):
        validate_config({
            "rain": {
                "lengths": [],
            },
        })


def test_box_border_types():
    for border in (
        "single",
        "double",
        "none",
    ):
        config = {
            "boxes": {
                "border": border,
            },
        }

        assert validate_config(config) == config


def test_invalid_box_border():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "border": "rounded",
            },
        })


def test_box_colors():
    config = {
        "boxes": {
            "border_color": "#FF0000",
            "text_color": "#00FF00",
            "accent_color": "#0000FF",
        },
    }

    assert validate_config(config) == config


def test_box_padding():
    config = {
        "boxes": {
            "padding": {
                "horizontal": 2,
                "vertical": 1,
            },
        },
    }

    assert validate_config(config) == config


def test_negative_padding_is_invalid():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "padding": {
                    "horizontal": -1,
                },
            },
        })


def test_box_position():
    config = {
        "boxes": {
            "items": [
                {
                    "type": "text",
                    "position": {
                        "horizontal": 5,
                        "vertical": -2,
                    },
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_unknown_box_type():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "items": [
                    {
                        "type": "does-not-exist",
                    },
                ],
            },
        })


def test_text_box():
    config = {
        "boxes": {
            "items": [
                {
                    "type": "text",
                    "text": "Hello",
                },
            ],
        },
    }

    assert validate_config(config) == config


@pytest.mark.parametrize(
    "key",
    [
        "clock_style",
        "clock_size",
    ],
)
def test_clock_enum_validation(key):
    config = {
        "boxes": {
            "items": [
                {
                    "type": "clock",
                    key: (
                        "single"
                        if key == "clock_style"
                        else "medium"
                    ),
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_clock_invalid_style():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "items": [
                    {
                        "type": "clock",
                        "clock_style": "invalid",
                    },
                ],
            },
        })


@pytest.mark.parametrize(
    "key",
    [
        "clock_24h",
        "show_seconds",
        "show_am_pm",
        "blink_colon",
        "show_date",
    ],
)
def test_clock_boolean_options(key):
    config = {
        "boxes": {
            "items": [
                {
                    "type": "clock",
                    key: True,
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_logo_validation():
    config = {
        "boxes": {
            "items": [
                {
                    "type": "logo",
                    "logo": "macos",
                    "colors": [
                        "#FFFFFF",
                        "#000000",
                    ],
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_logo_empty_name_is_invalid():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "items": [
                    {
                        "type": "logo",
                        "logo": "",
                    },
                ],
            },
        })


def test_sysinfo_sections():
    config = {
        "boxes": {
            "items": [
                {
                    "type": "sysinfo",
                    "sections": {
                        "system": True,
                        "display": True,
                        "hardware": False,
                        "disk": True,
                        "connectivity": False,
                    },
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_invalid_sysinfo_section():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "items": [
                    {
                        "type": "sysinfo",
                        "sections": {
                            "invalid": True,
                        },
                    },
                ],
            },
        })


def test_weather_with_location():
    config = {
        "boxes": {
            "items": [
                {
                    "type": "weather",
                    "location": "Rasht",
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_weather_with_coordinates():
    config = {
        "boxes": {
            "items": [
                {
                    "type": "weather",
                    "latitude": 37.28,
                    "longitude": 49.58,
                },
            ],
        },
    }

    assert validate_config(config) == config


def test_weather_requires_location_or_coordinates():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "items": [
                    {
                        "type": "weather",
                    },
                ],
            },
        })


def test_weather_latitude_range():
    with pytest.raises(ConfigError):
        validate_config({
            "boxes": {
                "items": [
                    {
                        "type": "weather",
                        "latitude": 100,
                        "longitude": 50,
                    },
                ],
            },
        })


def test_save_and_load_config(tmp_path):
    path = tmp_path / "config.yaml"

    config = {
        "background": "#101010",
        "rain": {
            "collision": True,
            "intensity": 10,
        },
        "boxes": {
            "border": "single",
            "items": [
                {
                    "type": "text",
                    "text": "Hello",
                },
            ],
        },
    }

    save_config(config, path)

    assert path.exists()

    loaded = load_config(path)

    assert loaded == config


def test_load_missing_custom_config_raises(tmp_path):
    path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_config(path)


def test_load_invalid_yaml(tmp_path):
    path = tmp_path / "config.yaml"

    path.write_text(
        "background: [invalid",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_config(path)