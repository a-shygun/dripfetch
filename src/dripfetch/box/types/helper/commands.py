"""Run external commands without ever raising."""

import subprocess


def run_command(*args, timeout=5):
    """Return the command's stripped stdout, or "" on any failure."""
    try:
        return subprocess.check_output(
            args,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        ).strip()
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return ""
