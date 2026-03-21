"""
Unit tests for monitoring infrastructure.
"""

import json
import logging
import time

from candles_feed.core.monitoring import (
    JSONFormatter,
    LogContext,
    LogLevel,
    MonitoringConfig,
    MonitoringManager,
    StructuredLogger,
)


class TestLogContext:
    """Tests for LogContext."""

    def test_default_context(self):
        """Test default context creation."""
        context = LogContext()
        assert context.component == ""
        assert context.operation == ""
        assert context.exchange == ""

    def test_context_with_values(self):
        """Test context creation with values."""
        context = LogContext(
            component="candles_feed",
            operation="start_stream",
            exchange="binance",
            trading_pair="BTC-USDT",
        )
        assert context.component == "candles_feed"
        assert context.operation == "start_stream"
        assert context.exchange == "binance"
        assert context.trading_pair == "BTC-USDT"

    def test_to_dict(self):
        """Test context conversion to dictionary."""
        context = LogContext(component="test", exchange="binance", request_id="123")
        result = context.to_dict()
        expected = {"component": "test", "exchange": "binance", "request_id": "123"}
        assert result == expected

    def test_to_dict_excludes_empty(self):
        """Test that empty values are excluded from dictionary."""
        context = LogContext(component="test", operation="")
        result = context.to_dict()
        assert result == {"component": "test"}


class TestMonitoringConfig:
    """Tests for MonitoringConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = MonitoringConfig()
        assert config.enable_structured_logging is True
        assert config.enable_metrics_collection is True
        assert config.log_level == LogLevel.INFO
        assert config.metrics_export_interval == 60.0
        assert config.log_format == "json"

    def test_custom_config(self):
        """Test custom configuration."""
        config = MonitoringConfig(
            enable_structured_logging=False,
            log_level=LogLevel.DEBUG,
            metrics_export_interval=30.0,
            log_format="standard",
        )
        assert config.enable_structured_logging is False
        assert config.log_level == LogLevel.DEBUG
        assert config.metrics_export_interval == 30.0
        assert config.log_format == "standard"


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_basic_formatting(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_func"
        record.module = "test_module"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert data["module"] == "test_module"
        assert data["function"] == "test_func"
        assert data["line"] == 10
        assert "timestamp" in data


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    def test_logger_creation(self):
        """Test logger creation."""
        config = MonitoringConfig()
        logger = StructuredLogger("test", config)
        assert logger.config == config
        assert logger.context.component == ""

    def test_logger_with_context(self):
        """Test logger creation with context."""
        config = MonitoringConfig()
        context = LogContext(component="test", exchange="binance")
        logger = StructuredLogger("test", config, context)
        assert logger.context == context

    def test_with_context(self):
        """Test creating logger with additional context."""
        logger = StructuredLogger("test")
        new_logger = logger.with_context(component="test", operation="stream")

        assert new_logger.context.component == "test"
        assert new_logger.context.operation == "stream"
        assert logger.context.component == ""


class TestMonitoringManager:
    """Tests for MonitoringManager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        config = MonitoringConfig()
        manager = MonitoringManager(config)
        assert manager.config == config
        assert manager._health_data["status"] == "healthy"

    def test_create_logger(self):
        """Test logger creation."""
        manager = MonitoringManager()
        context = LogContext(component="test")
        logger = manager.create_logger("test_logger", context)

        assert isinstance(logger, StructuredLogger)
        assert logger.context == context

    def test_record_metric(self):
        """Test metric recording."""
        config = MonitoringConfig()
        manager = MonitoringManager(config)

        manager.record_metric("test_metric", 42.0, {"tag": "value"})

        metrics = manager.get_metrics()
        assert "test_metric" in metrics
        assert len(metrics["test_metric"]) == 1
        assert metrics["test_metric"][0]["value"] == 42.0
        assert metrics["test_metric"][0]["tags"] == {"tag": "value"}

    def test_update_health_status(self):
        """Test health status updates."""
        manager = MonitoringManager()
        initial_time = manager._health_data["last_updated"]

        time.sleep(0.01)
        manager.update_health_status(active_connections=5, error_count=2)

        health = manager.get_health_status()
        assert health["active_connections"] == 5
        assert health["error_count"] == 2
        assert health["last_updated"] > initial_time

    def test_export_prometheus_metrics(self):
        """Test Prometheus metrics export."""
        manager = MonitoringManager()

        manager.record_metric("http_requests_total", 100.0, {"method": "GET"})
        manager.record_metric("response_time", 0.5)

        prometheus_output = manager.export_prometheus_metrics()

        assert 'http_requests_total{method="GET"} 100.0' in prometheus_output
        assert "response_time 0.5" in prometheus_output
