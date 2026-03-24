from hypothesis import given, settings
from hypothesis import strategies as st

from throttlekit.algorithms import SlidingWindowLog


@settings(deadline=500)
@given(
    limit=st.integers(min_value=1, max_value=100),
    window=st.integers(min_value=1, max_value=100),
    request_deltas=st.lists(
        st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=200,
    ),
)
def test_sliding_window_log_property(limit, window, request_deltas):
    """
    For any sequence of request times, the count of allowed requests
    in any window does not exceed the limit.
    """
    algo = SlidingWindowLog()
    key = "prop_key"

    now = 0.0
    allowed_timestamps = []

    for delta in request_deltas:
        now += delta
        clock = lambda: now

        result = algo.is_allowed(key, limit, window, clock=clock)
        if result.allowed:
            allowed_timestamps.append(now)

    for t in allowed_timestamps:
        count_in_window = sum(1 for ts in allowed_timestamps if t - window < ts <= t)
        assert count_in_window <= limit
