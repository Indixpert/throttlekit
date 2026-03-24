from __future__ import annotations

import collections
import threading
import time
from collections import defaultdict
from typing import Callable, Deque

from .base import Algorithm, RateLimitResult


class SlidingWindowLog(Algorithm):
    """
    Sliding Window Log algorithm implementation.

    This algorithm stores a log of request timestamps in a deque.
    Requests are allowed if the number of timestamps in the last `window`
    seconds is less than the `limit`.
    """

    def __init__(self) -> None:
        self._logs: dict[str, Deque[float]] = {}
        self._locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)

    def is_allowed(
        self, key: str, limit: int, window: int, *, clock: Callable[[], float] = time.monotonic
    ) -> RateLimitResult:
        with self._locks[key]:
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
                    retry_after=None,
                )
            else:
                retry_after = log[0] + window - now
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_after=retry_after,
                    retry_after=retry_after,
                )
