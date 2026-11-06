"""Temporary login lockout after repeated failures.

Failures are counted per (username, client IP). Counting per username alone would let anyone lock
another user out just by failing to log in as them; this way a lockout only affects the address
the failures came from, and the real user can still log in from their own. The per-IP request
limit on the login endpoint (see routers/auth.py) still bounds guessing from any one address.

The client IP is the address nginx resolved: the connecting address, or, for requests from a
reverse proxy listed in TRUSTED_PROXIES, the client address that proxy reported (see
trusted_proxies.py). Without TRUSTED_PROXIES, every request through a reverse proxy shares the
proxy's address.
"""
import time
import threading
from collections import defaultdict

WINDOW_SECONDS = 600    # 10-minute sliding window for failure counting
FAILURE_THRESHOLD = 5   # failures in the window before lockout applies
LOCKOUT_SECONDS = 300   # 5-minute cooldown after threshold is reached
_SWEEP_ABOVE = 10_000   # tracked keys before expired ones are swept out

_lock = threading.Lock()
_failures: dict[tuple[str, str], list[float]] = defaultdict(list)


def _key(username: str, client_ip: str | None) -> tuple[str, str]:
    return (username.strip().lower(), client_ip or "unknown")


def _prune(key: tuple[str, str], now: float) -> list[float]:
    cutoff = now - WINDOW_SECONDS
    times = [t for t in _failures.get(key, ()) if t > cutoff]
    if times:
        _failures[key] = times
    else:
        _failures.pop(key, None)
    return times


def _sweep(now: float) -> None:
    for key in list(_failures):
        _prune(key, now)


def is_locked(username: str, client_ip: str | None) -> bool:
    now = time.monotonic()
    with _lock:
        times = _prune(_key(username, client_ip), now)
        if len(times) < FAILURE_THRESHOLD:
            return False
        return (now - times[-FAILURE_THRESHOLD]) < LOCKOUT_SECONDS


def record_failure(username: str, client_ip: str | None) -> None:
    now = time.monotonic()
    with _lock:
        key = _key(username, client_ip)
        _prune(key, now)
        _failures[key].append(now)
        if len(_failures) > _SWEEP_ABOVE:
            _sweep(now)


def clear(username: str, client_ip: str | None) -> None:
    with _lock:
        _failures.pop(_key(username, client_ip), None)
