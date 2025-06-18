"""
External monitoring system integration.

This module provides integration with external monitoring systems including
Prometheus metrics export, health check endpoints, and monitoring dashboards.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import aiohttp
from aiohttp import web

from candles_feed.core.monitoring import MonitoringManager
from candles_feed.core.protocols import Logger


@dataclass
class MonitoringIntegrationConfig:
    """Configuration for external monitoring integration."""

    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    prometheus_path: str = "/metrics"
    health_check_enabled: bool = True
    health_check_port: int = 8080
    health_check_path: str = "/health"
    external_endpoints: dict[str, str] = field(default_factory=dict)
    check_interval_seconds: float = 30.0
    timeout_seconds: float = 10.0


class PrometheusMetricsExporter:
    """Exports metrics in Prometheus format."""

    def __init__(
        self,
        monitoring_manager: MonitoringManager,
        config: MonitoringIntegrationConfig,
        logger: Logger | None = None,
    ):
        """
        Initialize Prometheus metrics exporter.

        :param monitoring_manager: Core monitoring manager instance
        :param config: Integration configuration
        :param logger: Logger instance
        """
        self.monitoring_manager = monitoring_manager
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    def _format_prometheus_metrics(self) -> str:
        """Format metrics data in Prometheus format."""
        metrics_data = self.monitoring_manager.get_metrics()
        health_data = self.monitoring_manager.get_health_status()
        # Performance data is included in metrics_data

        lines = []

        # Add metadata
        lines.append("# HELP candles_feed_info Information about the candles feed service")
        lines.append("# TYPE candles_feed_info gauge")
        lines.append('candles_feed_info{version="1.0"} 1')
        lines.append("")

        # Health metrics
        lines.append("# HELP candles_feed_health Health status of the service")
        lines.append("# TYPE candles_feed_health gauge")
        status_value = 1 if health_data.get("status") == "healthy" else 0
        lines.append(f"candles_feed_health {status_value}")
        lines.append("")

        # Uptime
        uptime = health_data.get("uptime_seconds", 0)
        lines.append("# HELP candles_feed_uptime_seconds Service uptime in seconds")
        lines.append("# TYPE candles_feed_uptime_seconds counter")
        lines.append(f"candles_feed_uptime_seconds {uptime}")
        lines.append("")

        # Error count
        error_count = health_data.get("error_count", 0)
        lines.append("# HELP candles_feed_errors_total Total number of errors")
        lines.append("# TYPE candles_feed_errors_total counter")
        lines.append(f"candles_feed_errors_total {error_count}")
        lines.append("")

        # Memory usage
        memory_usage = health_data.get("memory_usage_mb", 0)
        lines.append("# HELP candles_feed_memory_usage_bytes Memory usage in bytes")
        lines.append("# TYPE candles_feed_memory_usage_bytes gauge")
        lines.append(f"candles_feed_memory_usage_bytes {memory_usage * 1024 * 1024}")
        lines.append("")

        # Performance metrics - extract timing metrics from the metrics data
        timing_metrics = {k: v for k, v in metrics_data.items() if "timing" in k.lower() or "duration" in k.lower()}
        if timing_metrics:
            lines.append("# HELP candles_feed_request_duration_seconds Request duration in seconds")
            lines.append("# TYPE candles_feed_request_duration_seconds histogram")

            for operation, timing in timing_metrics.items():
                if isinstance(timing, (int, float)):
                    operation_name = operation.replace("_timing", "").replace("_duration", "")
                    lines.append(
                        f'candles_feed_request_duration_seconds{{operation="{operation_name}"}} {timing}'
                    )

        # Custom metrics from monitoring manager
        for metric_name, metric_entries in metrics_data.items():
            if metric_entries and len(metric_entries) > 0:
                # Get the latest metric value (most recent entry)
                latest_entry = metric_entries[-1]
                metric_value = latest_entry["value"]
                tags = latest_entry.get("tags", {})
                
                safe_name = metric_name.replace("-", "_").replace(" ", "_").lower()
                lines.append(f"# HELP candles_feed_{safe_name} Custom metric: {metric_name}")
                lines.append(f"# TYPE candles_feed_{safe_name} gauge")
                
                # Format with tags if present
                if tags:
                    tag_pairs = [f'{k}="{v}"' for k, v in tags.items()]
                    tags_str = "{" + ",".join(tag_pairs) + "}"
                    lines.append(f"candles_feed_{safe_name}{tags_str} {metric_value}")
                else:
                    lines.append(f"candles_feed_{safe_name} {metric_value}")
                lines.append("")

        return "\n".join(lines)

    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """Handle Prometheus metrics requests."""
        try:
            metrics_text = self._format_prometheus_metrics()
            return web.Response(
                text=metrics_text, content_type="text/plain; version=0.0.4", charset="utf-8"
            )
        except Exception as e:
            self.logger.error(f"Failed to generate metrics: {e}")
            return web.Response(
                text="# Error generating metrics\n", status=500, content_type="text/plain"
            )

    async def start(self) -> None:
        """Start the Prometheus metrics server."""
        if not self.config.prometheus_enabled:
            self.logger.debug("Prometheus metrics export disabled")
            return

        try:
            self._app = web.Application()
            self._app.router.add_get(self.config.prometheus_path, self._metrics_handler)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            site = web.TCPSite(self._runner, "0.0.0.0", self.config.prometheus_port)
            await site.start()

            self.logger.info(
                f"Prometheus metrics server started on port {self.config.prometheus_port} "
                f"path {self.config.prometheus_path}"
            )
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus metrics server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Prometheus metrics server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        self.logger.info("Prometheus metrics server stopped")


class HealthCheckServer:
    """Provides health check endpoints for external monitoring."""

    def __init__(
        self,
        monitoring_manager: MonitoringManager,
        config: MonitoringIntegrationConfig,
        logger: Logger | None = None,
    ):
        """
        Initialize health check server.

        :param monitoring_manager: Core monitoring manager instance
        :param config: Integration configuration
        :param logger: Logger instance
        """
        self.monitoring_manager = monitoring_manager
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    async def _health_handler(self, request: web.Request) -> web.Response:
        """Handle health check requests."""
        try:
            health_data = self.monitoring_manager.get_health_status()

            # Determine overall health status
            status = health_data.get("status", "unknown")
            is_healthy = status == "healthy"

            response_data = {
                "status": status,
                "timestamp": time.time(),
                "uptime_seconds": health_data.get("uptime_seconds", 0),
                "memory_usage_mb": health_data.get("memory_usage_mb", 0),
                "error_count": health_data.get("error_count", 0),
                "checks": {
                    "memory": "ok" if health_data.get("memory_usage_mb", 0) < 500 else "warning",
                    "errors": "ok" if health_data.get("error_count", 0) == 0 else "warning",
                    "uptime": "ok" if health_data.get("uptime_seconds", 0) > 0 else "error",
                },
            }

            status_code = 200 if is_healthy else 503
            return web.json_response(response_data, status=status_code)

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return web.json_response(
                {"status": "error", "timestamp": time.time(), "error": str(e)}, status=503
            )

    async def _readiness_handler(self, request: web.Request) -> web.Response:
        """Handle readiness check requests."""
        try:
            # Check if the service is ready to handle requests
            health_data = self.monitoring_manager.get_health_status()
            uptime = health_data.get("uptime_seconds", 0)

            # Consider ready if uptime > 5 seconds and no critical errors
            error_count = health_data.get("error_count", 0)
            is_ready = uptime > 5 and error_count < 10

            response_data = {
                "ready": is_ready,
                "timestamp": time.time(),
                "uptime_seconds": uptime,
                "error_count": error_count,
            }

            status_code = 200 if is_ready else 503
            return web.json_response(response_data, status=status_code)

        except Exception as e:
            self.logger.error(f"Readiness check failed: {e}")
            return web.json_response(
                {"ready": False, "timestamp": time.time(), "error": str(e)}, status=503
            )

    async def _liveness_handler(self, request: web.Request) -> web.Response:
        """Handle liveness check requests."""
        try:
            # Simple liveness check - if we can respond, we're alive
            return web.json_response({"alive": True, "timestamp": time.time()}, status=200)
        except Exception as e:
            self.logger.error(f"Liveness check failed: {e}")
            return web.json_response(
                {"alive": False, "timestamp": time.time(), "error": str(e)}, status=503
            )

    async def start(self) -> None:
        """Start the health check server."""
        if not self.config.health_check_enabled:
            self.logger.debug("Health check server disabled")
            return

        try:
            self._app = web.Application()

            # Add health check endpoints
            self._app.router.add_get(self.config.health_check_path, self._health_handler)
            self._app.router.add_get("/health/readiness", self._readiness_handler)
            self._app.router.add_get("/health/liveness", self._liveness_handler)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            site = web.TCPSite(self._runner, "0.0.0.0", self.config.health_check_port)
            await site.start()

            self.logger.info(
                f"Health check server started on port {self.config.health_check_port} "
                f"path {self.config.health_check_path}"
            )
        except Exception as e:
            self.logger.error(f"Failed to start health check server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the health check server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        self.logger.info("Health check server stopped")


class ExternalMonitoringIntegration:
    """Main class for external monitoring integration."""

    def __init__(
        self,
        monitoring_manager: MonitoringManager,
        config: MonitoringIntegrationConfig | None = None,
        logger: Logger | None = None,
    ):
        """
        Initialize external monitoring integration.

        :param monitoring_manager: Core monitoring manager instance
        :param config: Integration configuration
        :param logger: Logger instance
        """
        self.monitoring_manager = monitoring_manager
        self.config = config or MonitoringIntegrationConfig()
        self.logger = logger or logging.getLogger(__name__)

        self.prometheus_exporter = PrometheusMetricsExporter(
            monitoring_manager, self.config, logger
        )
        self.health_check_server = HealthCheckServer(monitoring_manager, self.config, logger)

        self._monitoring_task: asyncio.Task | None = None

    async def _monitor_external_endpoints(self) -> None:
        """Monitor external endpoints for health status."""
        while True:
            try:
                for name, url in self.config.external_endpoints.items():
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                url,
                                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                            ) as response:
                                if response.status == 200:
                                    self.monitoring_manager.update_metrics(
                                        {
                                            f"external_endpoint_{name}_status": 1,
                                            f"external_endpoint_{name}_response_time": 0.1,  # Placeholder
                                        }
                                    )
                                else:
                                    self.monitoring_manager.update_metrics(
                                        {f"external_endpoint_{name}_status": 0}
                                    )
                                    self.logger.warning(
                                        f"External endpoint {name} returned {response.status}"
                                    )

                    except Exception as e:
                        self.monitoring_manager.update_metrics(
                            {f"external_endpoint_{name}_status": 0}
                        )
                        self.logger.error(f"Failed to check external endpoint {name}: {e}")

                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in external endpoint monitoring: {e}")
                await asyncio.sleep(self.config.check_interval_seconds)

    async def start(self) -> None:
        """Start all external monitoring components."""
        try:
            await self.prometheus_exporter.start()
            await self.health_check_server.start()

            if self.config.external_endpoints:
                self._monitoring_task = asyncio.create_task(self._monitor_external_endpoints())

            self.logger.info("External monitoring integration started")

        except Exception as e:
            self.logger.error(f"Failed to start external monitoring integration: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop all external monitoring components."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        await self.prometheus_exporter.stop()
        await self.health_check_server.stop()

        self.logger.info("External monitoring integration stopped")
