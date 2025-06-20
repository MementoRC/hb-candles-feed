"""
Unit tests for monitoring integration.
"""

import pytest

from candles_feed.core.monitoring import MonitoringConfig, MonitoringManager
from candles_feed.integration.monitoring import (
    ExternalMonitoringIntegration,
    HealthCheckServer,
    MonitoringIntegrationConfig,
    PrometheusMetricsExporter,
)


class TestPrometheusMetricsExporter:
    """Test Prometheus metrics exporter."""

    @pytest.fixture
    def monitoring_manager(self):
        """Create a monitoring manager for testing."""
        config = MonitoringConfig(
            enable_metrics_collection=True,
            enable_structured_logging=True,
            enable_performance_tracking=True,
        )
        return MonitoringManager(config)

    @pytest.fixture
    def integration_config(self):
        """Create integration configuration for testing."""
        return MonitoringIntegrationConfig(
            prometheus_enabled=True,
            prometheus_port=9999,  # Use test port
            health_check_enabled=False,  # Disable for isolated testing
        )

    @pytest.fixture
    def exporter(self, monitoring_manager, integration_config):
        """Create Prometheus exporter for testing."""
        return PrometheusMetricsExporter(monitoring_manager, integration_config)

    def test_format_prometheus_metrics(self, exporter, monitoring_manager):
        """Test Prometheus metrics formatting."""
        # Add some test metrics
        monitoring_manager.record_metric("test_metric_1", 42)
        monitoring_manager.record_metric("test_metric_2", 3.14)
        monitoring_manager.record_metric("test-metric-with-dashes", 100)

        # Update health status
        monitoring_manager.update_health_status(
            status="healthy", uptime_seconds=120, memory_usage_mb=256, error_count=0
        )

        metrics_text = exporter._format_prometheus_metrics()

        # Check basic structure
        assert "# HELP candles_feed_info" in metrics_text
        assert "# TYPE candles_feed_info gauge" in metrics_text
        assert 'candles_feed_info{version="1.0"} 1' in metrics_text

        # Check health metrics
        assert "candles_feed_health 1" in metrics_text
        assert "candles_feed_uptime_seconds 120" in metrics_text
        assert "candles_feed_errors_total 0" in metrics_text

        # Check custom metrics
        assert "candles_feed_test_metric_1 42" in metrics_text
        assert "candles_feed_test_metric_2 3.14" in metrics_text
        assert "candles_feed_test_metric_with_dashes 100" in metrics_text

    @pytest.mark.asyncio
    async def test_metrics_handler(self, exporter, monitoring_manager):
        """Test metrics HTTP handler."""
        from aiohttp.test_utils import make_mocked_request

        # Mock request
        request = make_mocked_request("GET", "/metrics")

        # Add test metrics
        monitoring_manager.record_metric("test_metric", 123)

        response = await exporter._metrics_handler(request)

        assert response.status == 200
        assert response.content_type == "text/plain"

        # Check response contains metrics
        response_text = response.text
        assert "candles_feed_test_metric 123" in response_text


class TestHealthCheckServer:
    """Test health check server."""

    @pytest.fixture
    def monitoring_manager(self):
        """Create a monitoring manager for testing."""
        config = MonitoringConfig()
        return MonitoringManager(config)

    @pytest.fixture
    def integration_config(self):
        """Create integration configuration for testing."""
        return MonitoringIntegrationConfig(
            health_check_enabled=True,
            health_check_port=8888,  # Use test port
            prometheus_enabled=False,  # Disable for isolated testing
        )

    @pytest.fixture
    def health_server(self, monitoring_manager, integration_config):
        """Create health check server for testing."""
        return HealthCheckServer(monitoring_manager, integration_config)

    @pytest.mark.asyncio
    async def test_health_handler(self, health_server, monitoring_manager):
        """Test health check handler."""
        from aiohttp.test_utils import make_mocked_request

        # Set healthy status
        monitoring_manager.update_health_status(
            status="healthy", uptime_seconds=60, memory_usage_mb=100, error_count=0
        )

        request = make_mocked_request("GET", "/health")
        response = await health_server._health_handler(request)

        assert response.status == 200

        # Parse JSON response
        import json

        response_data = json.loads(response.text)

        assert response_data["status"] == "healthy"
        assert response_data["uptime_seconds"] == 60
        assert response_data["memory_usage_mb"] == 100
        assert response_data["error_count"] == 0
        assert "checks" in response_data

    @pytest.mark.asyncio
    async def test_readiness_handler(self, health_server, monitoring_manager):
        """Test readiness check handler."""
        from aiohttp.test_utils import make_mocked_request

        # Set status with sufficient uptime
        monitoring_manager.update_health_status(
            uptime_seconds=10,  # > 5 seconds
            error_count=2,  # < 10 errors
        )

        request = make_mocked_request("GET", "/health/readiness")
        response = await health_server._readiness_handler(request)

        assert response.status == 200

        import json

        response_data = json.loads(response.text)
        assert response_data["ready"] is True

    @pytest.mark.asyncio
    async def test_liveness_handler(self, health_server):
        """Test liveness check handler."""
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request("GET", "/health/liveness")
        response = await health_server._liveness_handler(request)

        assert response.status == 200

        import json

        response_data = json.loads(response.text)
        assert response_data["alive"] is True


class TestExternalMonitoringIntegration:
    """Test external monitoring integration."""

    @pytest.fixture
    def monitoring_manager(self):
        """Create a monitoring manager for testing."""
        return MonitoringManager(MonitoringConfig())

    @pytest.fixture
    def integration_config(self):
        """Create integration configuration for testing."""
        return MonitoringIntegrationConfig(
            prometheus_enabled=False,
            health_check_enabled=False,
            external_endpoints={"test_service": "https://httpbin.org/status/200"},
        )

    @pytest.fixture
    def integration(self, monitoring_manager, integration_config):
        """Create monitoring integration for testing."""
        return ExternalMonitoringIntegration(monitoring_manager, integration_config)

    def test_initialization(self, integration):
        """Test integration initialization."""
        assert integration.monitoring_manager is not None
        assert integration.config is not None
        assert integration.prometheus_exporter is not None
        assert integration.health_check_server is not None
