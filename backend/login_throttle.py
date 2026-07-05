"""
Per-account login throttling.

Tracks failed login attempts by username in memory (single-worker safe).
After FAILURE_THRESHOLD failures within WINDOW_SECONDS, the account is
blocked for LOCKOUT_SECONDS.  A lockout is temporary and cannot be made
permanent by an attacker, which matters once usernames become visible to
other users via trade proposals.

State is not persisted across restarts — intentional.  A restart clears
all counters, which is an acceptable trade-off for simplicity and avoids
the "admin has to manually unlock" problem.
"""

import time
import threading
from collections import defaultdict

WINDOW_SECONDS = 600    # 10-minute sliding window for failure counting
FAILURE_THRESHOLD = 5   # failures in the window before lockout applies
LOCKOUT_SECONDS = 300   # 5-minute cooldown after threshold is reached

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
        # Check whether the most-recent burst is still within lockout window
        return (now - times[-FAILURE_THRESHOLD]) < LOCKOUT_SECONDS


def record_failure(username: str) -> None:
    now = time.monotonic()
    with _lock:
        _prune(username, now)
        _failures[username].append(now)


def clear(username: str) -> None:
    with _lock:
        _failures.pop(username, None)
