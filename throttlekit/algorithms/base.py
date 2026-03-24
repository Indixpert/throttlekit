import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

__all__ = ["Algorithm", "RateLimitResult"]


@dataclass(frozen=True)
class RateLimitResult:
    """
    The result of a rate limit check.

    Attributes:
        allowed: Whether the request is allowed.
        remaining: The number of requests remaining in the current window.
        reset_after: The number of seconds until the window resets.
        retry_after: The number of seconds to wait before retrying.
            This is only set if the request is not allowed.
    """

    allowed: bool
    remaining: int
    reset_after: float
    retry_after: float | None = None


class Algorithm(ABC):
    """Abstract base class for rate limiting algorithms."""

    @abstractmethod
    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> RateLimitResult:
        """
        Checks if a request is allowed for a given key.

        Args:
            key: The identifier for the rate limit.
            limit: The maximum number of requests allowed.
            window: The time window in seconds.
            clock: A callable that returns the current time in seconds.
                Defaults to `time.monotonic`.

        Returns:
            A `RateLimitResult` instance.
        """
        raise NotImplementedError
