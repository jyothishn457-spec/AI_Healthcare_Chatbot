"""
ratelimit.py
Per-IP sliding-window rate limiting, shared across routers.

Kept in its own module so every router can apply the same policy without
importing from main.py (which would create a circular import).
"""

import os
import time

from fastapi import HTTPException, Request

RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))   # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))         # requests / window / IP

_requests: dict[str, list[float]] = {}


def rate_limit(request: Request) -> None:
    """Enforce the sliding-window limit for the requesting IP.

    Usage: ``rate_limit(request)`` as the first line of a route, or as a
    FastAPI dependency via ``Depends(rate_limit)``.
    """
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = [t for t in _requests.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
    if len(window) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    window.append(now)
    _requests[ip] = window

    # Prune stale entries so the map does not grow forever.
    if len(_requests) > 5000:
        _requests.clear()
