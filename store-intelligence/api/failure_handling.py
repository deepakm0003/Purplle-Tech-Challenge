"""
Failure Handling Module.

Provides:
- Structured error responses (no stack traces)
- Database unavailable handling
- Redis unavailable handling
- Partial event ingestion
- Stale feed detection
- Graceful degradation

All errors return RFC 7807 Problem Details format.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class ErrorCode(str, Enum):
    """Standard error codes."""
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    REDIS_UNAVAILABLE = "REDIS_UNAVAILABLE"
    INVALID_EVENT_BATCH = "INVALID_EVENT_BATCH"
    PARTIAL_INGESTION = "PARTIAL_INGESTION"
    STALE_FEED = "STALE_FEED"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_STORE = "INVALID_STORE"
    INVALID_CAMERA = "INVALID_CAMERA"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ProblemDetail:
    """
    RFC 7807 Problem Details response.
    
    Standard error response format:
    {
        "type": "...",
        "title": "...",
        "status": 500,
        "detail": "...",
        "instance": "...",
        "timestamp": "...",
        "error_code": "...",
        "trace_id": "...",
        "recovery_suggestions": [...]
    }
    """
    
    def __init__(
        self,
        error_code: ErrorCode,
        title: str,
        detail: str,
        status_code: int,
        instance: Optional[str] = None,
        trace_id: Optional[str] = None,
        recovery_suggestions: Optional[list] = None
    ):
        """Initialize problem detail."""
        self.error_code = error_code
        self.title = title
        self.detail = detail
        self.status_code = status_code
        self.instance = instance
        self.trace_id = trace_id
        self.recovery_suggestions = recovery_suggestions or []
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': f"https://api.error.store-intelligence/{self.error_code.value}",
            'title': self.title,
            'status': self.status_code,
            'detail': self.detail,
            'instance': self.instance,
            'timestamp': self.timestamp,
            'error_code': self.error_code.value,
            'trace_id': self.trace_id,
            'recovery_suggestions': self.recovery_suggestions
        }


class DatabaseUnavailable(Exception):
    """Database is unavailable."""
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.DATABASE_UNAVAILABLE,
            title="Database Unavailable",
            detail="The database service is currently unavailable. Analytics may be delayed.",
            status_code=503,
            trace_id=trace_id,
            recovery_suggestions=[
                "Check database connectivity",
                "Verify database server status",
                "Retry request in 30 seconds"
            ]
        )


class RedisUnavailable(Exception):
    """Redis is unavailable."""
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.REDIS_UNAVAILABLE,
            title="Cache Unavailable",
            detail="Redis cache is unavailable. Queries may be slower.",
            status_code=503,
            trace_id=trace_id,
            recovery_suggestions=[
                "Check Redis connectivity",
                "Verify Redis server status",
                "Retry request in 10 seconds"
            ]
        )


class InvalidEventBatch(Exception):
    """Event batch is invalid."""
    
    def __init__(self, message: str, failed_indices: Optional[list] = None):
        """Initialize."""
        self.message = message
        self.failed_indices = failed_indices or []
        super().__init__(message)
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.INVALID_EVENT_BATCH,
            title="Invalid Event Batch",
            detail=self.message,
            status_code=400,
            trace_id=trace_id,
            recovery_suggestions=[
                "Verify event schema matches specification",
                "Check timestamp format (ISO-8601)",
                "Ensure all required fields are present",
                f"Review failed event indices: {self.failed_indices[:10]}"
            ]
        )


class PartialIngestion(Exception):
    """Some events failed ingestion."""
    
    def __init__(self, total: int, ingested: int, failed: int):
        """Initialize."""
        self.total = total
        self.ingested = ingested
        self.failed = failed
        super().__init__(f"Ingested {ingested}/{total} events")
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.PARTIAL_INGESTION,
            title="Partial Ingestion",
            detail=f"Successfully ingested {self.ingested} of {self.total} events",
            status_code=207,  # Multi-Status
            trace_id=trace_id,
            recovery_suggestions=[
                "Check failed events for schema violations",
                "Verify store_id and camera_id are valid",
                "Retry failed events in separate batch"
            ]
        )


class StaleFeed(Exception):
    """Event feed is stale (no new events)."""
    
    def __init__(self, minutes_stale: int):
        """Initialize."""
        self.minutes_stale = minutes_stale
        super().__init__(f"No events for {minutes_stale} minutes")
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.STALE_FEED,
            title="Stale Event Feed",
            detail=f"No events received in last {self.minutes_stale} minutes",
            status_code=503,
            trace_id=trace_id,
            recovery_suggestions=[
                "Check CCTV pipeline status",
                "Verify camera connections",
                "Check event queue for backlog",
                "Restart detection service if needed"
            ]
        )


class RateLimitExceeded(Exception):
    """Rate limit exceeded."""
    
    def __init__(self, limit: int, window_seconds: int):
        """Initialize."""
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit {limit}/{window_seconds}s exceeded")
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.RATE_LIMIT,
            title="Rate Limit Exceeded",
            detail=f"Request rate exceeds limit of {self.limit} per {self.window_seconds} seconds",
            status_code=429,
            trace_id=trace_id,
            recovery_suggestions=[
                "Implement exponential backoff",
                "Wait before retrying",
                "Consider batch processing"
            ]
        )


class InvalidStore(Exception):
    """Invalid store configuration."""
    
    def __init__(self, store_id: str):
        """Initialize."""
        self.store_id = store_id
        super().__init__(f"Store not found: {store_id}")
    
    def to_problem_detail(self, trace_id: Optional[str] = None) -> ProblemDetail:
        """Convert to ProblemDetail."""
        return ProblemDetail(
            error_code=ErrorCode.INVALID_STORE,
            title="Invalid Store",
            detail=f"Store '{self.store_id}' not found",
            status_code=404,
            trace_id=trace_id,
            recovery_suggestions=[
                "Verify store_id is correct",
                "Check store_layout.json configuration",
                "Ensure store is registered in system"
            ]
        )


class FailureHandler:
    """Centralized failure handling."""
    
    @staticmethod
    def handle_database_error(
        original_error: Exception,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle database errors.
        
        Args:
            original_error: Original exception
            trace_id: Trace ID for logging
            
        Returns:
            (response_dict, status_code)
        """
        logger.error(f"Database error: {str(original_error)[:100]}")
        
        problem = DatabaseUnavailable().to_problem_detail(trace_id)
        return problem.to_dict(), problem.status_code
    
    @staticmethod
    def handle_redis_error(
        original_error: Exception,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle Redis errors.
        
        Args:
            original_error: Original exception
            trace_id: Trace ID for logging
            
        Returns:
            (response_dict, status_code)
        """
        logger.warning(f"Redis error: {str(original_error)[:100]}")
        
        problem = RedisUnavailable().to_problem_detail(trace_id)
        return problem.to_dict(), problem.status_code
    
    @staticmethod
    def handle_validation_error(
        errors: list,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle validation errors.
        
        Args:
            errors: List of validation errors
            trace_id: Trace ID for logging
            
        Returns:
            (response_dict, status_code)
        """
        failed_indices = [e.get('index') for e in errors if 'index' in e]
        
        problem = InvalidEventBatch(
            f"Batch validation failed: {len(errors)} errors",
            failed_indices
        ).to_problem_detail(trace_id)
        
        return problem.to_dict(), problem.status_code
    
    @staticmethod
    def handle_partial_ingestion(
        total: int,
        ingested: int,
        failed: int,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle partial ingestion.
        
        Args:
            total: Total events
            ingested: Successfully ingested
            failed: Failed events
            trace_id: Trace ID for logging
            
        Returns:
            (response_dict, status_code)
        """
        problem = PartialIngestion(total, ingested, failed).to_problem_detail(trace_id)
        return problem.to_dict(), problem.status_code
    
    @staticmethod
    def handle_stale_feed(
        minutes_stale: int,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle stale feed.
        
        Args:
            minutes_stale: Minutes since last event
            trace_id: Trace ID for logging
            
        Returns:
            (response_dict, status_code)
        """
        logger.warning(f"Feed stale for {minutes_stale} minutes")
        
        problem = StaleFeed(minutes_stale).to_problem_detail(trace_id)
        return problem.to_dict(), problem.status_code
    
    @staticmethod
    def handle_internal_error(
        original_error: Exception,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle generic internal errors.
        
        Args:
            original_error: Original exception
            trace_id: Trace ID for logging
            
        Returns:
            (response_dict, status_code)
        """
        error_msg = str(original_error)[:100]
        logger.error(f"Internal error: {error_msg}")
        
        problem = ProblemDetail(
            error_code=ErrorCode.INTERNAL_ERROR,
            title="Internal Server Error",
            detail="An unexpected error occurred. Please try again later.",
            status_code=500,
            trace_id=trace_id,
            recovery_suggestions=[
                "Retry request in 30 seconds",
                "Contact support if error persists",
                f"Reference trace ID for debugging"
            ]
        )
        
        return problem.to_dict(), problem.status_code
