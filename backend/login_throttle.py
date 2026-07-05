import time
import threading
from collections import defaultdict

WINDOW_SECONDS = 600
FAILURE_THRESHOLD = 5
LOCKOUT_SECONDS = 300

_lock = threading.Lock()
_failures: dict[str, list[float]] = defaultdict(list)


def _prune(username: str, now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    _failures[username] = [t for t in _failures[username] if t > cutoff]


def is_locked(username: str) -> bool:
    now = time.monotonic()
    with _lock:
        _prune(username, now)
        times = _failures[username]
        if len(times) < FAILURE_THRESHOLD:
            return False
        return (now - times[-FAILURE_THRESHOLD]) < LOCKOUT_SECONDS


def record_failure(username: str) -> None:
    now = time.monotonic()
    with _lock:
        _prune(username, now)
        _failures[username].append(now)


def clear(username: str) -> None:
    with _lock:
        _failures.pop(username, None)
