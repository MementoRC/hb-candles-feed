"""
Notification integration for external services.

This module provides integration with the core notification system
to enable CI/CD event notifications and monitoring alerts.
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import Any

from candles_feed.core.monitoring import LogLevel, MonitoringManager
from candles_feed.core.notifications import (
    NotificationChannel,
    NotificationLevel,
    NotificationManager,
    NotificationMessage,
)
from candles_feed.core.protocols import Logger


@dataclass
class NotificationIntegrationConfig:
    """Configuration for notification integration."""

    # CI/CD event notifications
    notify_on_build_start: bool = True
    notify_on_build_success: bool = True
    notify_on_build_failure: bool = True
    notify_on_deployment: bool = True

    # Monitoring alert notifications
    notify_on_performance_degradation: bool = True
    notify_on_error_threshold: bool = True
    notify_on_health_check_failure: bool = True

    # Alert thresholds
    error_threshold_count: int = 5
    performance_degradation_threshold: float = 0.2  # 20% degradation

    # Channel preferences
    build_notification_channels: list[NotificationChannel] = None
    alert_notification_channels: list[NotificationChannel] = None

    def __post_init__(self):
        """Set default channel preferences."""
        if self.build_notification_channels is None:
            self.build_notification_channels = [NotificationChannel.SLACK]
        if self.alert_notification_channels is None:
            self.alert_notification_channels = [
                NotificationChannel.SLACK,
                NotificationChannel.DISCORD,
            ]


class NotificationIntegration:
    """Integrates notification system with CI/CD and monitoring events."""

    def __init__(
        self,
        notification_manager: NotificationManager,
        monitoring_manager: MonitoringManager | None = None,
        config: NotificationIntegrationConfig | None = None,
        logger: Logger | None = None,
    ):
        """
        Initialize notification integration.

        :param notification_manager: Core notification manager
        :param monitoring_manager: Core monitoring manager (optional)
        :param config: Integration configuration
        :param logger: Logger instance
        """
        self.notification_manager = notification_manager
        self.monitoring_manager = monitoring_manager
        self.config = config or NotificationIntegrationConfig()
        self.logger = logger or logging.getLogger(__name__)

        self._monitoring_task: asyncio.Task | None = None
        self._last_error_count = 0
        self._baseline_performance: dict[str, float] = {}

    def _map_log_level_to_notification_level(self, log_level: LogLevel) -> NotificationLevel:
        """Map monitoring log level to notification level."""
        mapping = {
            LogLevel.DEBUG: NotificationLevel.DEBUG,
            LogLevel.INFO: NotificationLevel.INFO,
            LogLevel.WARNING: NotificationLevel.WARNING,
            LogLevel.ERROR: NotificationLevel.ERROR,
            LogLevel.CRITICAL: NotificationLevel.CRITICAL,
        }
        return mapping.get(log_level, NotificationLevel.INFO)

    async def notify_build_event(
        self,
        event_type: str,
        project_name: str,
        branch: str,
        commit_sha: str,
        workflow_name: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send notification for CI/CD build events.

        :param event_type: Type of event (started, success, failure, deployment)
        :param project_name: Name of the project
        :param branch: Git branch name
        :param commit_sha: Git commit SHA
        :param workflow_name: Name of the workflow/pipeline
        :param details: Additional event details
        :return: True if notification sent successfully
        """
        # Check if notification is enabled for this event type
        should_notify = {
            "started": self.config.notify_on_build_start,
            "success": self.config.notify_on_build_success,
            "failure": self.config.notify_on_build_failure,
            "deployment": self.config.notify_on_deployment,
        }.get(event_type.lower(), False)

        if not should_notify:
            return True

        # Determine notification level based on event type
        level_map = {
            "started": NotificationLevel.INFO,
            "success": NotificationLevel.INFO,
            "failure": NotificationLevel.ERROR,
            "deployment": NotificationLevel.INFO,
        }
        level = level_map.get(event_type.lower(), NotificationLevel.INFO)

        # Create notification message
        title = f"🔨 {project_name}: {event_type.title()}"

        content_lines = [
            f"**Workflow:** {workflow_name}",
            f"**Branch:** {branch}",
            f"**Commit:** `{commit_sha[:8]}`",
        ]

        if details:
            if "duration" in details:
                content_lines.append(f"**Duration:** {details['duration']}")
            if "test_results" in details:
                content_lines.append(f"**Tests:** {details['test_results']}")
            if "url" in details:
                content_lines.append(f"**URL:** {details['url']}")

        message = NotificationMessage(
            title=title,
            content="\n".join(content_lines),
            level=level,
            metadata={
                "event_type": event_type,
                "project": project_name,
                "branch": branch,
                "commit": commit_sha,
                "workflow": workflow_name,
                **(details or {}),
            },
        )

        # Send notification with fallback channels
        success = await self.notification_manager.send_notification(
            message, fallback_channels=self.config.build_notification_channels[1:]
        )

        if success:
            self.logger.debug(f"Build event notification sent: {event_type}")
        else:
            self.logger.error(f"Failed to send build event notification: {event_type}")

        return success

    async def notify_monitoring_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        severity: LogLevel = LogLevel.WARNING,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send notification for monitoring alerts.

        :param alert_type: Type of alert (performance, error, health)
        :param title: Alert title
        :param message: Alert message
        :param severity: Alert severity level
        :param metadata: Additional alert metadata
        :return: True if notification sent successfully
        """
        # Check if notification is enabled for this alert type
        should_notify = {
            "performance": self.config.notify_on_performance_degradation,
            "error": self.config.notify_on_error_threshold,
            "health": self.config.notify_on_health_check_failure,
        }.get(alert_type.lower(), True)

        if not should_notify:
            return True

        # Map severity level
        notification_level = self._map_log_level_to_notification_level(severity)

        # Add emoji based on alert type and severity
        emoji_map = {
            ("performance", NotificationLevel.WARNING): "⚠️",
            ("performance", NotificationLevel.ERROR): "🚨",
            ("error", NotificationLevel.WARNING): "⚠️",
            ("error", NotificationLevel.ERROR): "❌",
            ("error", NotificationLevel.CRITICAL): "🚨",
            ("health", NotificationLevel.WARNING): "⚠️",
            ("health", NotificationLevel.ERROR): "❌",
            ("health", NotificationLevel.CRITICAL): "🚨",
        }

        emoji = emoji_map.get((alert_type.lower(), notification_level), "🔔")
        alert_title = f"{emoji} {title}"

        notification = NotificationMessage(
            title=alert_title,
            content=message,
            level=notification_level,
            metadata={"alert_type": alert_type, "severity": severity.value, **(metadata or {})},
        )

        # Send notification with fallback channels
        success = await self.notification_manager.send_notification(
            notification, fallback_channels=self.config.alert_notification_channels[1:]
        )

        if success:
            self.logger.debug(f"Monitoring alert notification sent: {alert_type}")
        else:
            self.logger.error(f"Failed to send monitoring alert notification: {alert_type}")

        return success

    async def _monitor_health_and_performance(self) -> None:
        """Background task to monitor health and performance metrics."""
        while True:
            try:
                if not self.monitoring_manager:
                    await asyncio.sleep(30)
                    continue

                health_data = self.monitoring_manager.get_health_status()
                performance_data = self.monitoring_manager.get_performance_data()

                # Check error threshold
                current_error_count = health_data.get("error_count", 0)
                if (
                    current_error_count > self._last_error_count
                    and current_error_count >= self.config.error_threshold_count
                ):
                    await self.notify_monitoring_alert(
                        alert_type="error",
                        title="Error Threshold Exceeded",
                        message=f"Error count has reached {current_error_count}, exceeding threshold of {self.config.error_threshold_count}",
                        severity=LogLevel.ERROR,
                        metadata={
                            "current_errors": current_error_count,
                            "threshold": self.config.error_threshold_count,
                        },
                    )

                self._last_error_count = current_error_count

                # Check performance degradation
                if performance_data:
                    for operation, current_time in performance_data.items():
                        if isinstance(current_time, int | float):
                            baseline_time = self._baseline_performance.get(operation)

                            if baseline_time is None:
                                # Establish baseline
                                self._baseline_performance[operation] = current_time
                            else:
                                # Check for degradation
                                degradation = (current_time - baseline_time) / baseline_time
                                if degradation > self.config.performance_degradation_threshold:
                                    await self.notify_monitoring_alert(
                                        alert_type="performance",
                                        title="Performance Degradation Detected",
                                        message=f"Operation '{operation}' performance degraded by {degradation:.1%}",
                                        severity=LogLevel.WARNING,
                                        metadata={
                                            "operation": operation,
                                            "current_time": current_time,
                                            "baseline_time": baseline_time,
                                            "degradation_percent": degradation * 100,
                                        },
                                    )

                # Check health status
                health_status = health_data.get("status", "unknown")
                if health_status not in ["healthy", "ok"]:
                    await self.notify_monitoring_alert(
                        alert_type="health",
                        title="Health Check Failure",
                        message=f"Service health status: {health_status}",
                        severity=LogLevel.ERROR,
                        metadata={
                            "health_status": health_status,
                            "uptime": health_data.get("uptime_seconds", 0),
                            "memory_usage": health_data.get("memory_usage_mb", 0),
                        },
                    )

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health and performance monitoring: {e}")
                await asyncio.sleep(30)

    async def start_monitoring(self) -> None:
        """Start background monitoring for alerts."""
        if self.monitoring_manager and not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._monitor_health_and_performance())
            self.logger.info("Started notification monitoring")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task
            self._monitoring_task = None
            self.logger.info("Stopped notification monitoring")

    async def send_startup_notification(self, project_name: str, version: str) -> bool:
        """
        Send notification when service starts up.

        :param project_name: Name of the project
        :param version: Version of the project
        :return: True if notification sent successfully
        """
        message = NotificationMessage(
            title=f"🚀 {project_name} Started",
            content=f"**Version:** {version}\n**Status:** Service successfully started",
            level=NotificationLevel.INFO,
            metadata={"event_type": "startup", "project": project_name, "version": version},
        )

        return await self.notification_manager.send_notification(message)

    async def send_shutdown_notification(self, project_name: str) -> bool:
        """
        Send notification when service shuts down.

        :param project_name: Name of the project
        :return: True if notification sent successfully
        """
        message = NotificationMessage(
            title=f"🛑 {project_name} Shutdown",
            content="**Status:** Service is shutting down",
            level=NotificationLevel.INFO,
            metadata={"event_type": "shutdown", "project": project_name},
        )

        return await self.notification_manager.send_notification(message)
