# Backends

ThrottleKit uses backends to store the state required for rate limiting (e.g., request timestamps or token counts).

## In-Memory Backend

The default backend stores all data in a Python dictionary in the local process memory.

- **`MemoryBackend`**: This is suitable for single-process applications, development, and testing.
- **Pros:** No external dependencies, very fast.
- **Cons:** State is lost on application restart. Does not work across multiple processes or servers.

## Redis Backend

For production environments, especially those with multiple workers or servers, a centralized backend like Redis is recommended.

*(A Redis backend is planned for a future release.)*

To use a Redis backend, you would pass an instance to the `Limiter`.

```python
# Example of future usage
import redis
from throttlekit import Limiter
from throttlekit.backends import RedisBackend

redis_client = redis.from_url("redis://localhost")
limiter = Limiter(backend=RedisBackend(redis_client))
```
