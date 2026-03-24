from hypothesis import given, settings
from hypothesis import strategies as st

from throttlekit.algorithms import SlidingWindowLog

from .test_shared import ManualClock

request_deltas = st.lists(
    st.floats(min_value=0.0, max_value=10.0), min_size=1, max_size=200
)


@settings(deadline=500)
@given(
    limit=st.integers(min_value=1, max_value=100),
    window=st.integers(min_value=1, max_value=60),
    deltas=request_deltas,
)
def test_sliding_window_log_property(
    limit: int, window: int, deltas: list[float]
) -> None:
    """
    Property-based test for SlidingWindowLog.

    For any sequence of requests, the number of allowed requests in any
    time window should not exceed the limit.
    """
    algo = SlidingWindowLog()
    clock = ManualClock()

    allowed_timestamps = []

    for delta in deltas:
        clock.advance(delta)
        if algo.is_allowed("key", limit, window, clock=clock).allowed:
            allowed_timestamps.append(clock())

    for t in allowed_timestamps:
        count = sum(1 for ts in allowed_timestamps if t - window < ts <= t)
        assert count <= limit
