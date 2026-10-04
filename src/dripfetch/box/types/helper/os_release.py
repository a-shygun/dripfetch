"""Parser for /etc/os-release, shared by logo detection and sysinfo."""


def read_os_release(path="/etc/os-release"):
    """Return the KEY=value pairs as a dict ({} if the file is unreadable)."""
    data = {}
    try:
        with open(path, encoding="utf-8") as file:
            for line in file:
                key, _, value = line.partition("=")
                data[key] = value.strip().strip('"')
    except OSError:
        return {}
    return data
