"""Shared config validators for box types.

The primitive validators live in ``app.config``, which imports the box
package lazily from ``validate_config``. These wrappers bind to it lazily
as well, so importing a box type never imports ``app.config`` up front.
"""


def _config():
    from ....app import config  # noqa: PLC0415

    return config


def error(path, message):
    return _config()._error(path, message)


def mapping(value, path):
    return _config()._mapping(value, path)


def string(value, path):
    return _config()._string(value, path)


def boolean(value, path):
    return _config()._bool(value, path)


def integer(value, path):
    return _config()._integer(value, path)


def number(value, path):
    return _config()._number(value, path)


def color(value, path):
    return _config()._color(value, path)


def enum(value, path, choices):
    return _config()._enum(value, path, choices)
