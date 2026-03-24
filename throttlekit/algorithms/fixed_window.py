import threading
import time
from typing import Callable

from .base import Algorithm, RateLimitResult


class FixedWindowCounter(Algorithm):
    """
    Fixed Window Counter algorithm implementation.

    This algorithm counts requests within discrete time windows. For a given
    window size, it divides time into buckets and counts requests per bucket.
    """

    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> RateLimitResult:
        with self._lock:
            now = clock()
            current_bucket = int(now // window)

            bucket, count = self._windows.get(key, (current_bucket, 0))

            if bucket != current_bucket:
                count = 0
                bucket = current_bucket

            if count < limit:
                count += 1
                self._windows[key] = (bucket, count)
                remaining = limit - count
                reset_after = (bucket + 1) * window - now
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_after=reset_after,
                )
            else:
                remaining = 0
                reset_after = (bucket + 1) * window - now
                return RateLimitResult(
                    allowed=False,
                    remaining=remaining,
                    reset_after=reset_after,
                    retry_after=reset_after,
                )
