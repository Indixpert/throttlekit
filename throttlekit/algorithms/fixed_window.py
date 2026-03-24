from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Callable

from .base import Algorithm, RateLimitResult


class FixedWindowCounter(Algorithm):
    """
    Fixed Window Counter algorithm implementation.

    This algorithm counts requests within discrete time windows.
    """

    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, int]] = {}
        self._locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

    def is_allowed(
        self, key: str, limit: int, window: int, *, clock: Callable[[], float] = time.monotonic
    ) -> RateLimitResult:
        with self._locks[key]:
            now = clock()
            current_bucket = int(now // window)

            bucket_id, count = self._windows.get(key, (current_bucket, 0))

            if bucket_id != current_bucket:
                count = 0
                bucket_id = current_bucket

            reset_after = (bucket_id + 1) * window - now

            if count < limit:
                count += 1
                self._windows[key] = (bucket_id, count)
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - count,
                    reset_after=reset_after,
                    retry_after=None,
                )
            else:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_after=reset_after,
                    retry_after=reset_after,
                )
