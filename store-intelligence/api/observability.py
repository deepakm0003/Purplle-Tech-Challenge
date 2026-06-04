"""
Observability Module.

Provides:
- Structured logging (loguru)
- Request tracing (trace IDs)
- Latency tracking
- Event throughput metrics
- Error counters
- Health diagnostics

All metrics are recorded in-memory and can be dumped.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from loguru import logger
import json

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class MetricsCollector:
    """Collects operational metrics."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize collector."""
        self.max_history = max_history
        self.request_latencies: deque = deque(maxlen=max_history)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.event_throughput: deque = deque(maxlen=max_history)
        self.operation_counters: Dict[str, int] = defaultdict(int)
        self.health_checks: List[Dict[str, Any]] = []
    
    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record operation latency."""
        self.request_latencies.append({
            'operation': operation,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.debug(f"Latency: {operation} took {latency_ms:.2f}ms")
    
    def record_error(self, error_type: str, error_msg: str) -> None:
        """Record error."""
        self.error_counts[error_type] += 1
        logger.error(f"Error [{error_type}]: {error_msg}")
    
    def record_event_throughput(self, count: int) -> None:
        """Record event throughput."""
        self.event_throughput.append({
            'count': count,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Throughput: {count} events processed")
    
    def record_operation(self, operation: str) -> None:
        """Record operation counter."""
        self.operation_counters[operation] += 1
    
    def record_health_check(self, service: str, status: str, details: Optional[str] = None) -> None:
        """Record health check result."""
        self.health_checks.append({
            'service': service,
            'status': status,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collected statistics."""
        # Calculate average latency
        avg_latency = 0
        if self.request_latencies:
            avg_latency = sum(r['latency_ms'] for r in self.request_latencies) / len(self.request_latencies)
        
        # Calculate throughput
        throughput_events = sum(r['count'] for r in self.event_throughput)
        
        return {
            'latency': {
                'average_ms': round(avg_latency, 2),
                'samples': len(self.request_latencies)
            },
            'errors': dict(self.error_counts),
            'throughput': {
                'total_events': throughput_events,
                'samples': len(self.event_throughput)
            },
            'operations': dict(self.operation_counters),
            'health_checks_count': len(self.health_checks)
        }


class RequestTracer:
    """Traces requests with unique trace IDs."""
    
    _active_traces: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self):
        """Initialize tracer."""
        self.trace_id: Optional[str] = None
        self.trace_log: List[Dict[str, Any]] = []
    
    @classmethod
    def start_trace(cls, operation: str, metadata: Optional[Dict] = None) -> str:
        """
        Start a new trace.
        
        Args:
            operation: Operation name
            metadata: Additional metadata
            
        Returns:
            Trace ID
        """
        from uuid import uuid4
        trace_id = str(uuid4())[:8]
        
        cls._active_traces[trace_id] = {
            'operation': operation,
            'start_time': datetime.utcnow(),
            'metadata': metadata or {},
            'spans': []
        }
        
        logger.info(f"[TRACE {trace_id}] Started: {operation}")
        return trace_id
    
    @classmethod
    def add_span(cls, trace_id: str, span_name: str, duration_ms: float) -> None:
        """
        Add span to trace.
        
        Args:
            trace_id: Trace identifier
            span_name: Span name
            duration_ms: Duration in milliseconds
        """
        if trace_id in cls._active_traces:
            cls._active_traces[trace_id]['spans'].append({
                'name': span_name,
                'duration_ms': duration_ms
            })
            logger.debug(f"[TRACE {trace_id}] Span {span_name}: {duration_ms:.2f}ms")
    
    @classmethod
    def end_trace(cls, trace_id: str, status: str = "SUCCESS") -> Dict[str, Any]:
        """
        End trace and return summary.
        
        Args:
            trace_id: Trace identifier
            status: Status (SUCCESS, ERROR)
            
        Returns:
            Trace summary
        """
        if trace_id not in cls._active_traces:
            return {}
        
        trace = cls._active_traces[trace_id]
        end_time = datetime.utcnow()
        total_duration = (end_time - trace['start_time']).total_seconds() * 1000
        
        summary = {
            'trace_id': trace_id,
            'operation': trace['operation'],
            'status': status,
            'duration_ms': round(total_duration, 2),
            'span_count': len(trace['spans']),
            'spans': trace['spans']
        }
        
        logger.info(f"[TRACE {trace_id}] Ended: {status} ({total_duration:.2f}ms)")
        
        del cls._active_traces[trace_id]
        return summary


# Global instances
_metrics = MetricsCollector()
_tracer = RequestTracer


def track_latency(operation: str) -> Callable:
    """
    Decorator to track operation latency.
    
    Args:
        operation: Operation name
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                latency_ms = (time.time() - start) * 1000
                _metrics.record_latency(operation, latency_ms)
        
        return wrapper
    
    return decorator


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics


def get_tracer() -> type:
    """Get global request tracer."""
    return _tracer


# ============================================================================
# Structured Logging Utilities
# ============================================================================

def log_event_ingestion(count: int, store_id: str, success_count: int, fail_count: int) -> None:
    """Log event ingestion."""
    logger.info(
        f"Event Ingestion",
        extra={
            'store_id': store_id,
            'total': count,
            'success': success_count,
            'failed': fail_count,
            'timestamp': datetime.utcnow().isoformat()
        }
    )


def log_api_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Log API request."""
    logger.info(
        f"API Request: {method} {path}",
        extra={
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': duration_ms
        }
    )


def log_database_query(query_type: str, table: str, duration_ms: float, row_count: int) -> None:
    """Log database query."""
    logger.debug(
        f"DB Query: {query_type} on {table}",
        extra={
            'query_type': query_type,
            'table': table,
            'duration_ms': duration_ms,
            'rows': row_count
        }
    )


def log_error(error_type: str, message: str, context: Optional[Dict] = None) -> None:
    """Log error with context."""
    context = context or {}
    logger.error(
        f"Error: {error_type}",
        extra={
            'error_type': error_type,
            'message': message,
            'context': context
        }
    )


def get_diagnostic_report() -> Dict[str, Any]:
    """Get complete diagnostic report."""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'metrics': _metrics.get_stats(),
        'active_traces': len(_tracer._active_traces),
        'uptime_seconds': 0  # Would be calculated if tracking start time
    }
