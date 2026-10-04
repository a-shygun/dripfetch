"""Tiny HTTP/JSON helpers for the weather box."""

import json
import urllib.parse
import urllib.request


def build_url(base, params):
    return f"{base}?{urllib.parse.urlencode(params)}"


def get_json(url, timeout, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)
