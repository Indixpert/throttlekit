import collections
import threading
import time
from typing import Callable, Deque

from .base import Algorithm, RateLimitResult


class SlidingWindowLog(Algorithm):
    """
    Sliding Window Log algorithm implementation.

    This algorithm keeps a log of timestamps for each request. Requests are
    allowed if the number of timestamps in the last `window` seconds is
    less than the `limit`.
    """

    def __init__(self) -> None:
        self._logs: dict[str, Deque[float]] = {}
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

            if key not in self._logs:
                self._logs[key] = collections.deque(maxlen=limit)

            log = self._logs[key]

            while log and now - log[0] > window:
                log.popleft()

            if len(log) < limit:
                log.append(now)
                remaining = limit - len(log)
                reset_after = (log[0] + window - now) if log else float(window)

                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_after=reset_after,
                )
            else:
                retry_after = log[0] + window - now if log else float(window)
                reset_after = retry_after

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_after=reset_after,
                    retry_after=retry_after,
                )
