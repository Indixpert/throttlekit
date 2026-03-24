import pytest

from throttlekit.algorithms import (
    Algorithm,
    FixedWindowCounter,
    SlidingWindowLog,
    TokenBucket,
)


@pytest.fixture(
    params=[
        FixedWindowCounter,
        SlidingWindowLog,
        TokenBucket,
    ],
    ids=[
        "FixedWindowCounter",
        "SlidingWindowLog",
        "TokenBucket",
    ],
)
def algorithm(request) -> Algorithm:
    """Fixture that provides an instance of each algorithm."""
    return request.param()
