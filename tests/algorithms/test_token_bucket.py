import time

import pytest

from throttlekit.algorithms import TokenBucket

from .test_shared import ManualClock


def test_token_bucket_burst_and_refill() -> None:
    """
    Tests a burst of requests, followed by a failure, and then a successful
    request after a refill period.
    """
    limit = 10
    window = 60
    clock = ManualClock(time.monotonic())
    algo = TokenBucket()

    for i in range(limit):
        result = algo.is_allowed("key", limit, window, clock=clock)
        assert result.allowed
        assert result.remaining == limit - (i + 1)

    result = algo.is_allowed("key", limit, window, clock=clock)
    assert not result.allowed
    assert result.remaining == 0
    assert result.retry_after is not None

    refill_one_token_time = window / limit
    assert result.retry_after == pytest.approx(refill_one_token_time)

    clock.advance(refill_one_token_time)

    result = algo.is_allowed("key", limit, window, clock=clock)
    assert result.allowed
    assert result.remaining == 0

    clock.advance(window)
    result = algo.is_allowed("key", limit, window, clock=clock)
    assert result.allowed
    assert result.remaining == limit - 1
