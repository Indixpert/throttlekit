from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from typing import Callable

from ..core import Limiter, parse_rate, RateLimitResult

def _default_key_func(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"

def _default_on_throttled(request: Request, result: RateLimitResult) -> Response:
    headers = {
        "Retry-After": str(result.retry_after),
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset),
    }
    return JSONResponse(
        {"error": "rate_limit_exceeded", "retry_after": result.retry_after},
        status_code=429,
        headers=headers,
    )

class ThrottleMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    def __init__(
        self,
        app: ASGIApp,
        limiter: Limiter,
        key_func: Callable[[Request], str] = _default_key_func,
        on_throttled: Callable[[Request, RateLimitResult], Response] = _default_on_throttled,
        default_limit: str | None = "100/hour",
    ):
        super().__init__(app)
        self.limiter = limiter
        self.key_func = key_func
        self.on_throttled = on_throttled
        self.default_limit = parse_rate(default_limit) if default_limit else None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        endpoint = None
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match:
                endpoint = getattr(route, 'endpoint', None)
                break

        rate_limit = getattr(endpoint, "_rate_limit", self.default_limit)

        if not rate_limit:
            return await call_next(request)

        limit, window = rate_limit
        key = self.key_func(request)

        result = self.limiter.is_allowed(key, limit, window)

        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset),
        }

        if not result.allowed:
            return self.on_throttled(request, result)

        response = await call_next(request)
        response.headers.update(headers)
        return response
