# ThrottleKit

A collection of rate limiting algorithms.

## Implemented Algorithms

*   **Token Bucket**: A flexible algorithm that allows for bursts of traffic.
*   **Sliding Window Log**: A precise algorithm that keeps a log of request timestamps.
*   **Fixed Window Counter**: A simple and memory-efficient algorithm that counts requests in discrete time windows.

## Usage

All algorithms share a common interface.

```python
from throttlekit.algorithms import TokenBucket, RateLimitResult

# Create an instance of the algorithm
limiter = TokenBucket()

# Check if a request is allowed
result: RateLimitResult = limiter.is_allowed(
    key="user_123",
    limit=100,      # 100 requests
    window=60,      # per 60 seconds
)

if result.allowed:
    print("Request allowed!")
    print(f"{result.remaining} requests remaining.")
else:
    print("Rate limit exceeded.")
    print(f"Try again in {result.retry_after:.2f} seconds.")
```
