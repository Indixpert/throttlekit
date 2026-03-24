from flask import Flask, request, g, abort, jsonify, Response
from typing import Callable

from ..core import Limiter, parse_rate, RateLimitResult

def _default_key_func() -> str:
    return request.remote_addr or "127.0.0.1"

class ThrottleFlask:
    def __init__(
        self,
        app: Flask | None = None,
        limiter: Limiter | None = None,
        key_func: Callable[[], str] = _default_key_func,
        default_limit: str | None = "100/hour",
    ):
        self.limiter = limiter
        self.key_func = key_func
        self.default_limit = parse_rate(default_limit) if default_limit else None
        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        self.app = app
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.register_error_handler(429, self._on_throttled)

    def _before_request(self):
        endpoint = request.endpoint
        if not self.limiter or not endpoint:
            return

        view_func = self.app.view_functions.get(endpoint)
        if not view_func:
            return

        rate_limit = getattr(view_func, "_rate_limit", self.default_limit)

        if not rate_limit:
            g.rate_limit_result = None
            return

        limit, window = rate_limit
        key = self.key_func()

        result = self.limiter.is_allowed(key, limit, window)
        g.rate_limit_result = result

        if not result.allowed:
            abort(429)

    def _after_request(self, response: Response) -> Response:
        result: RateLimitResult | None = g.get("rate_limit_result")

        if result:
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
            response.headers["X-RateLimit-Reset"] = str(result.reset)

        return response

    def _on_throttled(self, error) -> Response:
        result: RateLimitResult = g.get("rate_limit_result")

        headers = {
            "Retry-After": str(result.retry_after),
        }

        response = jsonify({"error": "rate_limit_exceeded", "retry_after": result.retry_after})
        response.status_code = 429
        response.headers.extend(headers)
        # Headers from _after_request are not applied on abort, so we must add them here.
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset)
        return response

def init_throttle(
    app: Flask,
    limiter: Limiter,
    key_func: Callable[[], str] = _default_key_func,
    default_limit: str | None = "100/hour"
) -> ThrottleFlask:
    """Initializes throttling for a Flask application."""
    throttle = ThrottleFlask(limiter=limiter, key_func=key_func, default_limit=default_limit)
    throttle.init_app(app)
    return throttle
