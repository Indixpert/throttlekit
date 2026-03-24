import time
from concurrent.futures import ThreadPoolExecutor

from throttlekit import Algorithm


def test_exact_limit_pass(algorithm: Algorithm):
    limit = 10
    window = 1
    for _ in range(limit):
        result = algorithm.is_allowed("key", limit, window)
        assert result.allowed


def test_over_limit_deny(algorithm: Algorithm):
    limit = 10
    window = 1
    for _ in range(limit):
        algorithm.is_allowed("key", limit, window)

    result = algorithm.is_allowed("key", limit, window)
    assert not result.allowed
    assert result.retry_after is not None
    assert result.retry_after > 0


def test_window_reset(algorithm: Algorithm):
    limit = 10
    window = 1

    now = time.monotonic()
    clock = lambda: now

    for _ in range(limit):
        assert algorithm.is_allowed("key", limit, window, clock=clock).allowed

    assert not algorithm.is_allowed("key", limit, window, clock=clock).allowed

    now += window + 0.1

    result = algorithm.is_allowed("key", limit, window, clock=clock)
    assert result.allowed


def test_concurrent_access(algorithm: Algorithm):
    limit = 20
    window = 2
    key = "concurrent_key"
    num_requests = 50

    def task():
        return algorithm.is_allowed(key, limit, window)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(task) for _ in range(num_requests)]
        results = [f.result() for f in futures]

    allowed_count = sum(1 for r in results if r.allowed)

    assert allowed_count == limit
