"""hb-logger compatibility shim for candles-feed's structured logging stack.

Backs candles-feed's bespoke ``StructuredLogger``/``JSONFormatter`` (see
``candles_feed.core.monitoring``) with the canonical ``hb-logger``
sub-package instead of raw ``logging.getLogger`` -- ADR 0001 Group D,
issue #78.

Preserves the pre-existing call-site API (``debug``/``info``/``warning``/
``error``/``exception``/``with_context``) so ``MonitoringManager`` and
``integration/*`` consumers need no changes; ``candles_feed.core.monitoring``
simply re-exports ``StructuredLoggerAdapter``/``StructuredJSONFormatter``
under their historical names (``StructuredLogger``/``JSONFormatter``).

Deliberately out of scope: ``MonitoringManager``'s non-logging
responsibilities (metrics collection, health status, Prometheus export) are
untouched -- this shim only replaces the logging backend.

Deferred imports: like ``hummingbot_network_client_adapter.py`` (PR #69),
importing ``candles_feed.core.monitoring`` at module scope here would create
a circular import (``core.monitoring`` imports this module for its logging
backend). Those imports are therefore deferred into method bodies; only
``TYPE_CHECKING``-guarded imports are used for annotations.
"""

from __future__ import annotations

import logging
import sys
import time
from json import dumps as json_dumps
from typing import TYPE_CHECKING, Any

from logger import HummingbotLogger, log_encoder

if TYPE_CHECKING:
    from candles_feed.core.monitoring import LogContext, MonitoringConfig

__all__ = [
    "StructuredJSONFormatter",
    "StructuredLoggerAdapter",
    "get_hb_logger",
]


def get_hb_logger(name: str) -> HummingbotLogger:
    """Return an hb-logger-backed logger for *name*.

    Importing hb-logger (``logger`` package) registers ``HummingbotLogger``
    as the process-wide logging class via ``logging.setLoggerClass``, so
    ``logging.getLogger`` already returns ``HummingbotLogger`` instances.
    """
    return logging.getLogger(name)  # type: ignore[return-value]


def _json_default(obj: object) -> str | dict[str, Any]:
    """JSON ``default=`` encoder: hb-logger's ``log_encoder``, falling back
    to ``str()`` for anything it doesn't recognize.

    ``log_encoder`` only knows ``Decimal``/``Enum``/dataclasses and raises
    ``TypeError`` for other objects; candles-feed's structured logging
    accepts arbitrary ``**kwargs`` as extra fields, so fall back to
    ``str()`` to preserve the previous (permissive) ``JSONFormatter``
    behaviour.
    """
    try:
        return log_encoder(obj)
    except TypeError:
        return str(obj)


class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging, hb-logger ``log_encoder``-aware."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        :param record: Log record to format
        :return: JSON formatted log string
        """
        log_data: dict[str, Any] = {
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

        return json_dumps(log_data, default=_json_default)


class StructuredLoggerAdapter:
    """Structured logger with context support, backed by hb-logger.

    Thin adapter over ``logger.HummingbotLogger`` preserving the call-site
    API of the former bespoke ``StructuredLogger``.
    """

    def __init__(
        self,
        name: str,
        config: MonitoringConfig | None = None,
        context: LogContext | None = None,
    ) -> None:
        """Initialize structured logger.

        :param name: Logger name
        :param config: Monitoring configuration
        :param context: Default log context
        """
        from candles_feed.core.monitoring import LogContext, MonitoringConfig

        self.config = config or MonitoringConfig()
        self.context = context or LogContext()
        self._logger: HummingbotLogger = get_hb_logger(name)

        # Configure logger if structured logging is enabled
        if self.config.enable_structured_logging and self.config.log_format == "json":
            self._configure_json_logging()

    def _configure_json_logging(self) -> None:
        """Configure JSON logging format."""
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredJSONFormatter())
            self._logger.addHandler(handler)
            self._logger.setLevel(getattr(logging, self.config.log_level.value))

    def with_context(self, **kwargs: Any) -> StructuredLoggerAdapter:
        """Create logger with additional context.

        :param kwargs: Context fields to add
        :return: New logger instance with extended context
        """
        from candles_feed.core.monitoring import LogContext

        new_context = LogContext(**{**self.context.__dict__, **kwargs})
        return StructuredLoggerAdapter(self._logger.name, self.config, new_context)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context."""
        self._log(logging.ERROR, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception message with traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal log method with context injection.

        :param level: Log level
        :param message: Log message
        :param kwargs: Additional context
        """
        from candles_feed.core.monitoring import LogContext

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
