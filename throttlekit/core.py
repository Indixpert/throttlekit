import time
from collections import defaultdict
from typing import Callable, Dict, Tuple, NamedTuple, Any


class MemoryBackend:
    """A simple in-memory backend for demonstration and single-process apps."""
    def __init__(self):
        self.cache: Dict[str, list[float]] = defaultdict(list)

    def get_timestamps(self, key: str) -> list[float]:
        return self.cache.get(key, [])

    def add_timestamp(self, key: str, window: int):
        now = time.time()
        # Evict old timestamps before adding a new one
        cutoff = now - window
        relevant_timestamps = [ts for ts in self.cache.get(key, []) if ts > cutoff]
        relevant_timestamps.append(now)
        self.cache[key] = relevant_timestamps


class RateLimitResult(NamedTuple):
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset: int
    retry_after: int | None


def parse_rate(rate: str) -> Tuple[int, int]:
    """Parses a rate string like '10/minute' into (10, 60)."""
    parts = rate.split('/')
    if len(parts) != 2:
        raise ValueError("Invalid rate format. Expected 'limit/period'.")

    limit = int(parts[0])
    period_str = parts[1].lower()

    multipliers = {
        's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
        'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
        'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
        'd': 86400, 'day': 86400, 'days': 86400,
    }

    for unit, multiplier in multipliers.items():
        if period_str.endswith(unit):
            num_str = period_str[:-len(unit)]
            num = int(num_str) if num_str else 1
            window = num * multiplier
            return limit, window

    raise ValueError(f"Unknown time period: {parts[1]}")


class Limiter:
    """The core rate limiter."""
    def __init__(self, backend: Any = None):
        self.backend = backend or MemoryBackend()

    def is_allowed(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Implements a fixed-window rate limiting algorithm.
        """
        timestamps = self.backend.get_timestamps(key)
        now = time.time()

        relevant_timestamps = [ts for ts in timestamps if ts > now - window]

        is_allowed = len(relevant_timestamps) < limit

        if is_allowed:
            self.backend.add_timestamp(key, window)
            remaining = limit - (len(relevant_timestamps) + 1)
            reset_time = now + (window - (now - relevant_timestamps[0]) if relevant_timestamps else window)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset=int(reset_time),
                retry_after=None
            )
        else:
            remaining = 0
            reset_time = relevant_timestamps[0] + window
            retry_after = int(reset_time - now)
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=remaining,
                reset=int(reset_time),
                retry_after=max(0, retry_after)
            )

    def limit(self, rate_string: str) -> Callable:
        """
        A decorator that applies a rate limit to a FastAPI or Flask endpoint.
        """
        def decorator(func: Callable) -> Callable:
            setattr(func, "_rate_limit", parse_rate(rate_string))
            return func
        return decorator
