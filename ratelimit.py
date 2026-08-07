"""
Simple in-memory fixed-window rate limiter.

NOTE: This is per-process state. It is safe with a single server process /
worker. If you scale to multiple uvicorn workers or multiple servers, replace
this with a shared store (e.g. Redis) using the same interface below.
"""
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.time()
        bucket = self._hits[key]
        # Drop timestamps outside the current window.
        while bucket and bucket[0] <= now - self.window_seconds:
            bucket.pop(0)

        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        bucket.append(now)

    def client_key(self, request: Request) -> str:
        """Identify a client by IP so limits are per-client."""
        return request.client.host if request.client else "unknown"
