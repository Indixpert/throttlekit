# Flask Middleware

ThrottleKit integrates with Flask using its `before_request` and `after_request` hooks.

## `init_throttle`

To enable rate limiting, call `init_throttle` with your Flask app instance.

```python
from flask import Flask
from throttlekit import Limiter
from throttlekit.middleware.flask import init_throttle

app = Flask(__name__)
limiter = Limiter()

init_throttle(
    app,
    limiter=limiter,
    default_limit="100/hour"
)
```

### Configuration

The `init_throttle` function accepts the following parameters:

- `app`: Your Flask `app` instance.
- `limiter`: An instance of `throttlekit.Limiter`.
- `key_func` (optional): A callable that returns a unique identifier string for the client. Defaults to using `request.remote_addr`.
- `default_limit` (optional): A rate limit string (e.g., `"100/hour"`) to apply to all routes that don't have a specific limit set via the `@limiter.limit` decorator.

### Per-Route Limits

You can specify different limits for different routes using the `@limiter.limit` decorator.

```python
@app.route("/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    # ...
    return jsonify(status="ok")
```

### Custom Key Function

By default, requests are identified by their IP address. You can provide a custom function to identify users based on other criteria.

```python
from flask import request

def key_from_header() -> str:
    # Identify client by a custom header
    api_key = request.headers.get("X-Api-Key")
    return api_key or request.remote_addr

init_throttle(
    app,
    limiter=limiter,
    key_func=key_from_header
)
```
