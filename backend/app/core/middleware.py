"""
HTTP middleware classes for request processing.

Provides security headers, request ID tracking, and size limits.
"""

import logging
import uuid

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size.

    Checks Content-Length header and rejects oversized requests
    before they're processed.
    """

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize middleware.

        Args:
            app: ASGI application
            max_size: Maximum request size in bytes (default 10MB)
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and check size limit."""
        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(f"Request rejected: size {content_length} exceeds limit {self.max_size}")
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size is {self.max_size / (1024 * 1024):.1f}MB",
                )

        response = await call_next(request)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID for tracking.

    Generates UUID for each request, stores in request.state,
    and adds X-Request-ID response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add request ID."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add to logger context for this request
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers."""
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
