"""Rate limiter in-memory — 100 req/min par IP"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException

_requests: dict = defaultdict(list)

def rate_limit(max_per_min: int = 100):
    """FastAPI dependency — lève 429 si dépassé."""
    async def _check(request: Request):
        ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown").split(",")[0].strip()
        now = time.time()
        # Purge old entries
        _requests[ip] = [t for t in _requests[ip] if now - t < 60]
        if len(_requests[ip]) >= max_per_min:
            raise HTTPException(status_code=429, detail={
                "error": "Too many requests",
                "limit": max_per_min,
                "window": "60 seconds",
                "retry_after": 60
            })
        _requests[ip].append(now)
    return _check
