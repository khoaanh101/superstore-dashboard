"""
access_middleware.py — HTTP access log middleware.

Logs one line to the "access" logger for every request:
    METHOD  /path  STATUS  123ms  IP  "User-Agent"

Static frontend assets (/frontend/*) and /health are excluded from the
access log to avoid thousands of trivial lines on every page load.
"""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("access")

# Paths whose log lines would just be noise
_SKIP_PREFIXES = ("/frontend/", "/health")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log every non-static HTTP request to the access logger."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip static assets and health-checks
        if request.url.path.startswith(_SKIP_PREFIXES):
            return await call_next(request)

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            ip = _client_ip(request)
            ua = request.headers.get("user-agent", "-")
            logger.error(
                "%-6s %-40s ERR   %7.1fms  %s  %r",
                request.method,
                request.url.path,
                elapsed_ms,
                ip,
                ua,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        ip = _client_ip(request)
        ua = request.headers.get("user-agent", "-")

        logger.info(
            "%-6s %-40s %d   %7.1fms  %s  %r",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            ip,
            ua,
        )
        return response


def _client_ip(request: Request) -> str:
    """
    Extract the real client IP.
    Respects X-Forwarded-For when the app runs behind a reverse proxy.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"
