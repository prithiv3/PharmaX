"""Request Correlation ID & Duration Logging Middleware for Traceability."""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middleware")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to inject/propagate X-Request-ID headers and log request duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        request_id = request.headers.get("X-Request-ID")
        if not request_id or not request_id.strip():
            request_id = str(uuid.uuid4())
        else:
            request_id = request_id.strip()

        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Log sanitized request summary (strictly excludes tokens, passwords, DB URLs, request bodies)
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} "
            f"{duration_ms}ms X-Request-ID={request_id}"
        )

        return response
