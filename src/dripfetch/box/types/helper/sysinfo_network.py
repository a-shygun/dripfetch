"""Network address and battery readings for the sysinfo box."""

import ipaddress
import socket

import psutil

_PREFERRED_INTERFACES = ("en0", "eth0", "wlan0")


def ip_address():
    """First non-loopback IPv4 address as "addr/prefix", or "Unknown"."""
    try:
        interfaces = psutil.net_if_addrs()
    except (OSError, RuntimeError):
        return "Unknown"

    names = _PREFERRED_INTERFACES + tuple(
        name for name in interfaces if name not in _PREFERRED_INTERFACES
    )

    for name in names:
        for address in interfaces.get(name, []):
            if address.family != socket.AF_INET or address.address.startswith("127."):
                continue

            try:
                prefix = ipaddress.IPv4Network(
                    f"0.0.0.0/{address.netmask}"
                ).prefixlen
            except ValueError:
                continue

            return f"{address.address}/{prefix}"

    return "Unknown"


def battery():
    """Return (percent, plugged_in, adapter_label)."""
    try:
        status = psutil.sensors_battery()
    except (AttributeError, OSError):
        status = None

    if status is None:
        return "Unknown", False, "Unknown"

    connected = status.power_plugged

    return (
        f"{status.percent:.0f}",
        connected,
        "AC Power" if connected else "Battery",
    )
