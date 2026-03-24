import threading
import time
from typing import Callable

from .base import Algorithm, RateLimitResult


class TokenBucket(Algorithm):
    """
    Token Bucket algorithm implementation.

    This algorithm maintains a bucket of tokens for each key. Tokens are
    refilled at a constant rate. A request is allowed if there is at least
    one token in the bucket.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, float]] = {}
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
            tokens, last_refill = self._buckets.get(key, (float(limit), now))

            refill_rate = limit / window
            elapsed = now - last_refill
            tokens_to_add = elapsed * refill_rate

            tokens = min(float(limit), tokens + tokens_to_add)
            last_refill = now

            if tokens >= 1.0:
                tokens -= 1.0
                self._buckets[key] = (tokens, last_refill)
                reset_after = (limit - tokens) / refill_rate if refill_rate > 0 else float("inf")
                return RateLimitResult(
                    allowed=True,
                    remaining=int(tokens),
                    reset_after=reset_after,
                )
            else:
                self._buckets[key] = (tokens, last_refill)
                retry_after = (1.0 - tokens) / refill_rate if refill_rate > 0 else float("inf")
                reset_after = (limit - tokens) / refill_rate if refill_rate > 0 else float("inf")
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_after=reset_after,
                    retry_after=retry_after,
                )
