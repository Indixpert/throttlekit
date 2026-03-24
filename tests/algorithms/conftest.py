import pytest

from throttlekit.algorithms import (
    FixedWindowCounter,
    SlidingWindowLog,
    TokenBucket,
)
from throttlekit.algorithms.base import Algorithm


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
def algorithm(request: pytest.FixtureRequest) -> Algorithm:
    """Fixture that provides an instance of each algorithm."""
    return request.param()
