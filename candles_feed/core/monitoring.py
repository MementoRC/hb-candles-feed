"""
Monitoring and logging infrastructure for the Candle Feed framework.

This module provides structured logging, metrics collection, and monitoring
integration compatible with Hummingbot's monitoring infrastructure.
"""

import json
import logging
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar, Protocol


class LogLevel(Enum):
    """Log levels for structured logging."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MonitoringConfig:
    """Configuration for monitoring and logging systems."""

    def __init__(
        self,
        enable_structured_logging: bool = True,
        enable_metrics_collection: bool = True,
        log_level: LogLevel = LogLevel.INFO,
        metrics_export_interval: float = 60.0,
        enable_performance_tracking: bool = True,
        max_log_buffer_size: int = 1000,
        log_format: str = "json",  # "json" or "standard"
    ):
        """Initialize monitoring configuration.

        :param enable_structured_logging: Enable JSON structured logging
        :param enable_metrics_collection: Enable metrics collection
        :param log_level: Minimum log level to record
        :param metrics_export_interval: Interval for metrics export in seconds
        :param enable_performance_tracking: Track performance metrics
        :param max_log_buffer_size: Maximum log entries to buffer
        :param log_format: Log format ("json" or "standard")
        """
        self.enable_structured_logging = enable_structured_logging
        self.enable_metrics_collection = enable_metrics_collection
        self.log_level = log_level
        self.metrics_export_interval = metrics_export_interval
        self.enable_performance_tracking = enable_performance_tracking
        self.max_log_buffer_size = max_log_buffer_size
        self.log_format = log_format


@dataclass
class LogContext:
    """Context information for structured logging."""

    component: str = ""
    operation: str = ""
    exchange: str = ""
    trading_pair: str = ""
    request_id: str = ""
    session_id: str = ""
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {k: v for k, v in self.__dict__.items() if v}


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        :param record: Log record to format
        :return: JSON formatted log string
        """
        log_data = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context if available
        if hasattr(record, "context") and record.context:
            log_data.update(record.context.to_dict())

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """Structured logger with context support."""

    def __init__(
        self, name: str, config: MonitoringConfig | None = None, context: LogContext | None = None
    ):
        """Initialize structured logger.

        :param name: Logger name
        :param config: Monitoring configuration
        :param context: Default log context
        """
        self.config = config or MonitoringConfig()
        self.context = context or LogContext()
        self._logger = logging.getLogger(name)

        # Configure logger if structured logging is enabled
        if self.config.enable_structured_logging and self.config.log_format == "json":
            self._configure_json_logging()

    def _configure_json_logging(self):
        """Configure JSON logging format."""
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter())
            self._logger.addHandler(handler)
            self._logger.setLevel(getattr(logging, self.config.log_level.value))

    def with_context(self, **kwargs) -> "StructuredLogger":
        """Create logger with additional context.

        :param kwargs: Context fields to add
        :return: New logger instance with extended context
        """
        new_context = LogContext(**{**self.context.__dict__, **kwargs})
        return StructuredLogger(self._logger.name, self.config, new_context)

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log(logging.ERROR, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception message with traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with context injection.

        :param level: Log level
        :param message: Log message
        :param kwargs: Additional context
        """
        if self.config.enable_structured_logging:
            # Merge only valid LogContext fields
            context_fields = {k: v for k, v in kwargs.items() if hasattr(LogContext(), k)}
            context = LogContext(**{**self.context.__dict__, **context_fields})
            extra = {"context": context}

            # Add remaining kwargs as extra fields
            non_context_kwargs = {k: v for k, v in kwargs.items() if not hasattr(LogContext(), k)}
            extra.update(non_context_kwargs)

            self._logger.log(level, message, extra=extra)
        else:
            self._logger.log(level, message)


class MonitoringProtocol(Protocol):
    """Protocol for monitoring integration."""

    def log_event(self, event: str, context: dict[str, Any]) -> None:
        """Log an operational event."""
        ...

    def record_metric(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a metric value."""
        ...

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status."""
        ...


class MonitoringManager:
    """Central monitoring manager for candles-feed operations."""

    _instance: ClassVar["MonitoringManager | None"] = None

    def __init__(self, config: MonitoringConfig | None = None):
        """Initialize monitoring manager.

        :param config: Monitoring configuration
        """
        self.config = config or MonitoringConfig()
        self._metrics_data: dict[str, Any] = {}
        self._health_data: dict[str, Any] = {
            "status": "healthy",
            "last_updated": time.time(),
            "active_connections": 0,
            "error_count": 0,
            "total_requests": 0,
        }
        self._logger = StructuredLogger("candles_feed.monitoring", self.config)

    @classmethod
    def get_instance(cls, config: MonitoringConfig | None = None) -> "MonitoringManager":
        """Get singleton monitoring manager instance.

        :param config: Monitoring configuration
        :return: MonitoringManager instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def create_logger(self, name: str, context: LogContext | None = None) -> StructuredLogger:
        """Create a structured logger with monitoring integration.

        :param name: Logger name
        :param context: Default context for the logger
        :return: Configured structured logger
        """
        return StructuredLogger(name, self.config, context)

    def log_event(self, event: str, context: dict[str, Any]) -> None:
        """Log an operational event.

        :param event: Event name
        :param context: Event context
        """
        if self.config.enable_structured_logging:
            self._logger.info(f"Event: {event}", **context)

    def record_metric(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a metric value.

        :param name: Metric name
        :param value: Metric value
        :param tags: Optional metric tags
        """
        if self.config.enable_metrics_collection:
            timestamp = time.time()
            metric_data = {"value": value, "timestamp": timestamp, "tags": tags or {}}

            if name not in self._metrics_data:
                self._metrics_data[name] = []

            self._metrics_data[name].append(metric_data)

            # Log metric if structured logging is enabled
            if self.config.enable_structured_logging:
                self._logger.info(
                    f"Metric recorded: {name}",
                    metric_name=name,
                    metric_value=value,
                    metric_tags=tags or {},
                )

    def increment_counter(self, name: str, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric.

        :param name: Counter name
        :param tags: Optional tags
        """
        self.record_metric(name, 1.0, tags)

    def record_timing(self, name: str, duration: float, tags: dict[str, str] | None = None) -> None:
        """Record a timing metric.

        :param name: Timing metric name
        :param duration: Duration in seconds
        :param tags: Optional tags
        """
        self.record_metric(f"{name}_duration", duration, tags)

    def update_health_status(self, **kwargs) -> None:
        """Update health status data.

        :param kwargs: Health status fields to update
        """
        self._health_data.update(kwargs)
        self._health_data["last_updated"] = time.time()

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status.

        :return: Health status dictionary
        """
        return self._health_data.copy()

    def get_metrics(self) -> dict[str, Any]:
        """Get collected metrics data.

        :return: Metrics data dictionary
        """
        return self._metrics_data.copy()

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format.

        :return: Prometheus format metrics string
        """
        lines = []
        for metric_name, metric_data in self._metrics_data.items():
            if metric_data:
                latest = metric_data[-1]
                tags_str = ""
                if latest["tags"]:
                    tag_pairs = [f'{k}="{v}"' for k, v in latest["tags"].items()]
                    tags_str = "{" + ",".join(tag_pairs) + "}"

                lines.append(f"{metric_name}{tags_str} {latest['value']}")

        return "\n".join(lines)

    def clear_metrics(self) -> None:
        """Clear collected metrics data."""
        self._metrics_data.clear()
