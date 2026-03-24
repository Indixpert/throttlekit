from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

__all__ = ["Algorithm", "RateLimitResult"]


@dataclass(frozen=True)
class RateLimitResult:
    """
    The result of a rate limit check.
    """

    allowed: bool
    """Whether the request is allowed."""

    remaining: int
    """The number of requests remaining in the current window."""

    reset_after: float
    """The number of seconds until the rate limit resets."""

    retry_after: float | None = None
    """The number of seconds to wait before retrying."""


class Algorithm(ABC):
    """
    Abstract base class for all rate limiting algorithms.
    """

    @abstractmethod
    def is_allowed(
        self, key: str, limit: int, window: int, *, clock: Callable[[], float] = time.monotonic
    ) -> RateLimitResult:
        """
        Checks if a request is allowed for a given key.

        Args:
            key: A unique identifier for the entity being rate-limited.
            limit: The maximum number of requests allowed in a window.
            window: The time window in seconds.
            clock: A callable that returns the current time in seconds.
                   Defaults to `time.monotonic`.

        Returns:
            A `RateLimitResult` instance.
        """
        raise NotImplementedError
