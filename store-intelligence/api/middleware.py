"""
FastAPI Middleware

Custom middleware for request/response processing.
Handles logging, tracing, and performance monitoring.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    
    The request ID is generated from UUID4 and added to:
    - Request scope (accessible via request.state.request_id)
    - Response headers (X-Request-ID)
    - Log records (via LogRecord.request_id)
    
    This enables request tracing across logs and responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID.
        
        Args:
            request: FastAPI Request
            call_next: Next middleware/route handler
            
        Returns:
            Response with request ID header
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP requests and responses.
    
    Logs:
    - Request method, path, query string
    - Response status code
    - Request/response latency
    - Request ID for tracing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log timing.
        
        Args:
            request: FastAPI Request
            call_next: Next middleware/route handler
            
        Returns:
            Response with timing logged
        """
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        response = await call_next(request)

        latency_ms = (time.time() - start_time) * 1000
        
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING

        logger.log(
            log_level,
            f"{request.method} {request.url.path} - {response.status_code} - {latency_ms:.2f}ms",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            }
        )

        return response
