from concurrent.futures import ThreadPoolExecutor, as_completed

from throttlekit.algorithms.base import Algorithm


class ManualClock:
    def __init__(self, initial_time: float = 0.0):
        self._time = initial_time

    def __call__(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


def test_exact_limit_pass(algorithm: Algorithm) -> None:
    """Test that exactly `limit` requests are allowed."""
    limit = 10
    window = 60
    clock = ManualClock()

    for _ in range(limit):
        result = algorithm.is_allowed("key", limit, window, clock=clock)
        assert result.allowed

    result = algorithm.is_allowed("key", limit, window, clock=clock)
    assert not result.allowed
    assert result.remaining == 0
    assert result.retry_after is not None
    assert result.retry_after > 0


def test_over_limit_deny(algorithm: Algorithm) -> None:
    """Test that the `limit + 1`-th request is denied."""
    limit = 5
    window = 60
    clock = ManualClock()

    for _ in range(limit):
        algorithm.is_allowed("key", limit, window, clock=clock)

    result = algorithm.is_allowed("key", limit, window, clock=clock)
    assert not result.allowed


def test_window_reset(algorithm: Algorithm) -> None:
    """Test that the rate limit resets after the window passes."""
    limit = 10
    window = 60
    clock = ManualClock()

    for _ in range(limit):
        assert algorithm.is_allowed("key", limit, window, clock=clock).allowed

    assert not algorithm.is_allowed("key", limit, window, clock=clock).allowed

    clock.advance(window + 0.1)  # Add a small delta to avoid edge cases

    result = algorithm.is_allowed("key", limit, window, clock=clock)
    assert result.allowed


def test_concurrent_access(algorithm: Algorithm) -> None:
    """Test that the algorithm is thread-safe."""
    limit = 100
    window = 10
    key = "concurrent_key"
    num_workers = 20
    requests_per_worker = 10

    def do_request() -> bool:
        return algorithm.is_allowed(key, limit, window).allowed

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(do_request)
            for _ in range(requests_per_worker * num_workers)
        ]

        results = [future.result() for future in as_completed(futures)]

    allowed_count = sum(1 for r in results if r)

    assert allowed_count == limit
