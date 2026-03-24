from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Callable

from .base import Algorithm, RateLimitResult


class TokenBucket(Algorithm):
    """
    Token Bucket algorithm implementation.

    This algorithm refills tokens at a constant rate. Requests are allowed
    if there is at least one token in the bucket.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, float]] = {}
        self._locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

    def is_allowed(
        self, key: str, limit: int, window: int, *, clock: Callable[[], float] = time.monotonic
    ) -> RateLimitResult:
        with self._locks[key]:
            now = clock()
            tokens, last_refill = self._buckets.get(key, (float(limit), now))

            refill_rate = limit / window if window > 0 else float("inf")
            elapsed = now - last_refill

            tokens = min(limit, tokens + elapsed * refill_rate)
            last_refill = now

            time_to_full = (limit - tokens) / refill_rate if refill_rate > 0 else 0.0

            if tokens >= 1.0:
                tokens -= 1.0
                self._buckets[key] = (tokens, last_refill)
                return RateLimitResult(
                    allowed=True,
                    remaining=int(tokens),
                    reset_after=time_to_full,
                    retry_after=None,
                )
            else:
                self._buckets[key] = (tokens, last_refill)
                retry_after = (1.0 - tokens) / refill_rate if refill_rate > 0 else float("inf")
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_after=time_to_full,
                    retry_after=retry_after,
                )
