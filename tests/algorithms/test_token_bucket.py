import time

from throttlekit.algorithms import TokenBucket


def test_token_bucket_burst():
    """A burst of `limit` requests should all pass."""
    algo = TokenBucket()
    limit = 10
    window = 60
    for i in range(limit):
        res = algo.is_allowed("key", limit, window)
        assert res.allowed
        assert res.remaining == limit - (i + 1)


def test_token_bucket_over_burst():
    """The `limit + 1`-th request should fail."""
    algo = TokenBucket()
    limit = 10
    window = 60
    for _ in range(limit):
        assert algo.is_allowed("key", limit, window).allowed

    res = algo.is_allowed("key", limit, window)
    assert not res.allowed
    assert res.retry_after is not None
    assert res.retry_after > 0


def test_token_bucket_refill():
    """After the window passes, requests should be allowed again."""
    algo = TokenBucket()
    limit = 10
    window = 1

    now = time.monotonic()
    clock = lambda: now

    for _ in range(limit):
        assert algo.is_allowed("key", limit, window, clock=clock).allowed

    res = algo.is_allowed("key", limit, window, clock=clock)
    assert not res.allowed

    now += window
    res = algo.is_allowed("key", limit, window, clock=clock)
    assert res.allowed
    assert res.remaining == limit - 1
