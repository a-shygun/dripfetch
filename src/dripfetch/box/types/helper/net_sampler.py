"""Network throughput sampling for the net box."""

import time
from collections import deque


def resolve_reader():
    """Return a () -> (bytes_recv, bytes_sent) callable, or None.

    Uses psutil if available, else /proc/net/dev on Linux.
    """
    try:
        import psutil  # noqa: PLC0415

        def read_psutil():
            counters = psutil.net_io_counters(pernic=False)
            return counters.bytes_recv, counters.bytes_sent

        # Sanity check it actually works before committing to it.
        read_psutil()
        return read_psutil
    except Exception:  # noqa: BLE001
        pass

    def read_proc():
        recv_total = 0
        sent_total = 0
        with open("/proc/net/dev", encoding="utf-8") as handle:
            lines = handle.readlines()[2:]
        for line in lines:
            iface, _, rest = line.partition(":")
            iface = iface.strip()
            if not iface or iface == "lo":
                continue
            fields = rest.split()
            if len(fields) < 9:
                continue
            recv_total += int(fields[0])
            sent_total += int(fields[8])
        return recv_total, sent_total

    try:
        read_proc()
        return read_proc
    except Exception:  # noqa: BLE001
        return None


class NetSampler:
    """Polls the byte counters and keeps rolling download/upload histories."""

    def __init__(self, history_length, interval):
        self.interval = interval
        self.download_history = deque([0] * history_length, maxlen=history_length)
        self.upload_history = deque([0] * history_length, maxlen=history_length)
        self.download_rate = 0.0
        self.upload_rate = 0.0

        self._last_time = None
        self._last_counters = None
        self._reader = resolve_reader()
        self.error = None if self._reader else "Network stats unavailable"

    @property
    def peak(self):
        """Largest sample currently buffered in either direction."""
        return max(
            max(self.download_history, default=0),
            max(self.upload_history, default=0),
        )

    def update(self):
        if not self._reader:
            return

        now = time.monotonic()

        if self._last_time is not None and now - self._last_time < self.interval:
            return

        try:
            counters = self._reader()
        except Exception as exc:  # noqa: BLE001
            self.error = f"Network stats unavailable: {exc}"
            return

        if self._last_time is not None and self._last_counters is not None:
            elapsed = now - self._last_time
            if elapsed > 0:
                recv_delta = counters[0] - self._last_counters[0]
                sent_delta = counters[1] - self._last_counters[1]
                # Counters can wrap/reset (interface reset, 32-bit
                # rollover); treat a negative delta as "no data" rather
                # than plotting a nonsensical negative rate.
                self.download_rate = max(0.0, recv_delta / elapsed)
                self.upload_rate = max(0.0, sent_delta / elapsed)
                self.download_history.append(self.download_rate)
                self.upload_history.append(self.upload_rate)
                self.error = None

        self._last_time = now
        self._last_counters = counters
