# FastAPI Middleware

ThrottleKit provides a Starlette-compatible middleware for easy integration with FastAPI.

## `ThrottleMiddleware`

The primary component is `ThrottleMiddleware`. You add it to your application's middleware stack.

```python
from fastapi import FastAPI
from throttlekit import Limiter
from throttlekit.middleware.fastapi import ThrottleMiddleware

app = FastAPI()
limiter = Limiter()

app.add_middleware(
    ThrottleMiddleware,
    limiter=limiter,
    default_limit="100/hour"
)
```

### Configuration

The middleware can be configured with the following parameters:

- `limiter`: An instance of `throttlekit.Limiter`.
- `key_func` (optional): A callable that takes a `Request` and returns a unique identifier string for the client. Defaults to using `request.client.host`.
- `on_throttled` (optional): A callable that takes a `Request` and a `RateLimitResult` and returns a `Response` when a request is throttled. Defaults to a JSON response with status 429.
- `default_limit` (optional): A rate limit string (e.g., `"100/hour"`) to apply to all routes that don't have a specific limit set via the `@limiter.limit` decorator.

### Per-Route Limits

You can specify different limits for different routes using the `@limiter.limit` decorator.

```python
@app.get("/login")
@limiter.limit("10/minute")
async def login():
    # ...
    return {"status": "ok"}
```

### Custom Key Function

By default, requests are identified by their IP address. You can provide a custom function to identify users based on other criteria, like an API key or a JWT.

```python
from starlette.requests import Request

def key_from_jwt(request: Request) -> str:
    # Fictional: extract user ID from a JWT in the Authorization header
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    # In a real app, you would decode and verify the JWT here
    payload = {"user_id": "user123"} # dummy payload
    return payload.get("user_id", request.client.host)

app.add_middleware(
    ThrottleMiddleware,
    limiter=limiter,
    key_func=key_from_jwt
)
```
