"""Behavioural tests for candles_feed.integration.notifications."""

import asyncio

import pytest

from candles_feed.core.monitoring import LogLevel
from candles_feed.core.notifications import NotificationChannel, NotificationLevel
from candles_feed.integration.notifications import (
    NotificationIntegration,
    NotificationIntegrationConfig,
)


@pytest.fixture
def manager(mocker):
    m = mocker.MagicMock()
    m.send_notification = mocker.AsyncMock(return_value=True)
    return m


@pytest.fixture
def logger(mocker):
    return mocker.MagicMock()


def make(manager, logger, monitoring=None, **cfg) -> NotificationIntegration:
    return NotificationIntegration(
        manager, monitoring, NotificationIntegrationConfig(**cfg), logger
    )


class TestConfig:
    def test_default_channels(self):
        cfg = NotificationIntegrationConfig()
        assert cfg.build_notification_channels == [NotificationChannel.SLACK]
        assert cfg.alert_notification_channels == [
            NotificationChannel.SLACK,
            NotificationChannel.DISCORD,
        ]

    def test_custom_channels_kept(self):
        cfg = NotificationIntegrationConfig(
            build_notification_channels=[NotificationChannel.EMAIL],
            alert_notification_channels=[],
        )
        assert cfg.build_notification_channels == [NotificationChannel.EMAIL]
        assert cfg.alert_notification_channels == []


class TestInit:
    def test_defaults(self, manager):
        i = NotificationIntegration(manager)
        assert i.monitoring_manager is None
        assert isinstance(i.config, NotificationIntegrationConfig)
        assert i.logger is not None

    @pytest.mark.parametrize(
        "log,expected",
        [
            (LogLevel.DEBUG, NotificationLevel.DEBUG),
            (LogLevel.INFO, NotificationLevel.INFO),
            (LogLevel.WARNING, NotificationLevel.WARNING),
            (LogLevel.ERROR, NotificationLevel.ERROR),
            (LogLevel.CRITICAL, NotificationLevel.CRITICAL),
        ],
    )
    def test_level_mapping(self, manager, log, expected):
        assert (
            NotificationIntegration(manager)._map_log_level_to_notification_level(log) is expected
        )

    def test_level_mapping_unknown_defaults_info(self, manager):
        i = NotificationIntegration(manager)
        assert i._map_log_level_to_notification_level("nope") is NotificationLevel.INFO  # type: ignore[arg-type]


class TestBuildEvent:
    @pytest.mark.parametrize(
        "event,flag",
        [
            ("started", "notify_on_build_start"),
            ("success", "notify_on_build_success"),
            ("failure", "notify_on_build_failure"),
            ("deployment", "notify_on_deployment"),
        ],
    )
    async def test_disabled_event_skips(self, manager, logger, event, flag):
        i = make(manager, logger, **{flag: False})
        assert await i.notify_build_event(event, "p", "b", "abc", "w") is True
        manager.send_notification.assert_not_called()

    async def test_unknown_event_skips(self, manager, logger):
        assert await make(manager, logger).notify_build_event("weird", "p", "b", "abc", "w") is True
        manager.send_notification.assert_not_called()

    async def test_failure_with_details(self, manager, logger):
        i = make(manager, logger)
        details = {"duration": "5m", "test_results": "10 passed", "url": "http://x", "extra": 1}
        assert await i.notify_build_event("FAILURE", "proj", "main", "0123456789", "CI", details)
        msg = manager.send_notification.call_args[0][0]
        assert msg.level is NotificationLevel.ERROR
        assert msg.title == "🔨 proj: Failure"
        for line in (
            "**Workflow:** CI",
            "**Branch:** main",
            "**Commit:** `01234567`",
            "**Duration:** 5m",
            "**Tests:** 10 passed",
            "**URL:** http://x",
        ):
            assert line in msg.content
        assert msg.metadata["extra"] == 1 and msg.metadata["event_type"] == "FAILURE"
        assert manager.send_notification.call_args[1]["fallback_channels"] == []
        logger.debug.assert_called_once_with("Build event notification sent: FAILURE")

    async def test_partial_details(self, manager, logger):
        await make(manager, logger).notify_build_event(
            "success", "p", "b", "abcdefghi", "w", {"x": 1}
        )
        msg = manager.send_notification.call_args[0][0]
        assert msg.level is NotificationLevel.INFO
        assert "Duration" not in msg.content and "Tests" not in msg.content

    async def test_fallback_channels_and_failure(self, manager, logger):
        manager.send_notification.return_value = False
        i = make(
            manager,
            logger,
            build_notification_channels=[NotificationChannel.SLACK, NotificationChannel.WEBHOOK],
        )
        assert await i.notify_build_event("started", "p", "b", "abc", "w") is False
        assert manager.send_notification.call_args[1]["fallback_channels"] == [
            NotificationChannel.WEBHOOK
        ]
        logger.error.assert_called_once_with("Failed to send build event notification: started")


class TestMonitoringAlert:
    @pytest.mark.parametrize(
        "alert,flag",
        [
            ("performance", "notify_on_performance_degradation"),
            ("error", "notify_on_error_threshold"),
            ("health", "notify_on_health_check_failure"),
        ],
    )
    async def test_disabled_skips(self, manager, logger, alert, flag):
        i = make(manager, logger, **{flag: False})
        assert await i.notify_monitoring_alert(alert, "t", "m") is True
        manager.send_notification.assert_not_called()

    @pytest.mark.parametrize(
        "alert,sev,emoji",
        [
            ("performance", LogLevel.WARNING, "⚠️"),
            ("error", LogLevel.ERROR, "❌"),
            ("health", LogLevel.CRITICAL, "🚨"),
            ("custom", LogLevel.INFO, "🔔"),
        ],
    )
    async def test_emoji_and_payload(self, manager, logger, alert, sev, emoji):
        i = make(manager, logger)
        assert await i.notify_monitoring_alert(alert, "Title", "Body", sev, {"k": "v"}) is True
        msg = manager.send_notification.call_args[0][0]
        assert msg.title == f"{emoji} Title"
        assert msg.content == "Body"
        assert msg.metadata == {"alert_type": alert, "severity": sev.value, "k": "v"}
        # default alert channels: SLACK, DISCORD -> DISCORD is fallback
        assert manager.send_notification.call_args[1]["fallback_channels"] == [
            NotificationChannel.DISCORD
        ]
        logger.debug.assert_called_once()

    async def test_failure_logged(self, manager, logger):
        manager.send_notification.return_value = False
        i = make(manager, logger, alert_notification_channels=[NotificationChannel.SLACK])
        assert await i.notify_monitoring_alert("error", "t", "m") is False
        assert manager.send_notification.call_args[1]["fallback_channels"] == []
        logger.error.assert_called_once_with("Failed to send monitoring alert notification: error")


class FakeMonitoring:
    def __init__(self, health=None, metrics=None):
        self.health = health if health is not None else {"status": "healthy"}
        self.metrics = metrics or {}

    def get_health_status(self):
        return self.health

    def get_metrics(self):
        return self.metrics


class OneCycle:
    """asyncio.sleep replacement that cancels the loop after N sleeps."""

    def __init__(self, cycles=1):
        self.cycles = cycles
        self.calls = []

    async def __call__(self, delay):
        self.calls.append(delay)
        if len(self.calls) >= self.cycles:
            raise asyncio.CancelledError


@pytest.fixture
def sleeper(monkeypatch):
    s = OneCycle()
    monkeypatch.setattr("candles_feed.integration.notifications.asyncio.sleep", s)
    return s


class TestMonitorLoop:
    async def test_no_monitoring_manager_sleeps(self, manager, logger, sleeper):
        i = make(manager, logger)
        await i._monitor_health_and_performance()
        assert sleeper.calls == [30]
        manager.send_notification.assert_not_called()

    async def test_healthy_no_alert(self, manager, logger, sleeper):
        i = make(manager, logger, FakeMonitoring({"status": "ok", "error_count": 1}))
        await i._monitor_health_and_performance()
        manager.send_notification.assert_not_called()
        assert i._last_error_count == 1

    async def test_error_threshold_alert(self, manager, logger, sleeper):
        i = make(manager, logger, FakeMonitoring({"status": "ok", "error_count": 6}))
        await i._monitor_health_and_performance()
        msg = manager.send_notification.call_args[0][0]
        assert "Error Threshold Exceeded" in msg.title
        assert msg.metadata["current_errors"] == 6 and msg.metadata["threshold"] == 5
        assert i._last_error_count == 6

    async def test_error_not_repeated_when_count_unchanged(self, manager, logger, sleeper):
        i = make(manager, logger, FakeMonitoring({"status": "ok", "error_count": 6}))
        i._last_error_count = 6
        await i._monitor_health_and_performance()
        manager.send_notification.assert_not_called()

    async def test_health_failure_alert(self, manager, logger, sleeper):
        health = {"status": "degraded", "uptime_seconds": 12, "memory_usage_mb": 99}
        i = make(manager, logger, FakeMonitoring(health))
        await i._monitor_health_and_performance()
        msg = manager.send_notification.call_args[0][0]
        assert "Health Check Failure" in msg.title
        assert msg.level is NotificationLevel.ERROR
        assert msg.metadata["health_status"] == "degraded"
        assert msg.metadata["uptime"] == 12
        assert msg.metadata["memory_usage"] == 99

    async def test_missing_status_is_unknown_alert(self, manager, logger, sleeper):
        i = make(manager, logger, FakeMonitoring({}))
        await i._monitor_health_and_performance()
        assert "unknown" in manager.send_notification.call_args[0][0].content

    async def test_performance_baseline_established(self, manager, logger, sleeper):
        metrics = {
            "fetch_duration": [{"value": 1.0}],
            "Request_Timing": [{"value": 2}],
            "empty_duration": [],
            "other": [{"value": 5}],
            "bad_duration": [{"value": "n/a"}],
        }
        i = make(manager, logger, FakeMonitoring(metrics=metrics))
        await i._monitor_health_and_performance()
        assert i._baseline_performance == {"fetch_duration": 1.0, "Request_Timing": 2}
        manager.send_notification.assert_not_called()

    async def test_performance_degradation_alert(self, manager, logger, sleeper):
        metrics = {"op_duration": [{"value": 0.1}, {"value": 2.0}], "ok_duration": [{"value": 1.0}]}
        i = make(manager, logger, FakeMonitoring(metrics=metrics))
        i._baseline_performance = {"op_duration": 1.0, "ok_duration": 1.0}
        await i._monitor_health_and_performance()
        assert manager.send_notification.await_count == 1
        msg = manager.send_notification.call_args[0][0]
        assert "Performance Degradation Detected" in msg.title
        assert "100.0%" in msg.content
        assert msg.metadata["operation"] == "op_duration"
        assert msg.metadata["degradation_percent"] == pytest.approx(100.0)

    async def test_exception_logged_and_continues(self, manager, logger, sleeper, mocker):
        sleeper.cycles = 2
        mon = FakeMonitoring()
        mocker.patch.object(
            mon, "get_health_status", side_effect=[RuntimeError("down"), {"status": "ok"}]
        )
        i = make(manager, logger, mon)
        await i._monitor_health_and_performance()
        logger.error.assert_called_once_with("Error in health and performance monitoring: down")
        assert sleeper.calls == [30, 30]


class TestLifecycle:
    async def test_start_without_monitoring_manager_noop(self, manager, logger):
        i = make(manager, logger)
        await i.start_monitoring()
        assert i._monitoring_task is None

    async def test_start_and_stop(self, manager, logger):
        i = make(manager, logger, FakeMonitoring())
        await i.start_monitoring()
        task = i._monitoring_task
        assert task is not None
        await i.start_monitoring()  # second start is a no-op
        assert i._monitoring_task is task
        logger.info.assert_called_once_with("Started notification monitoring")
        await asyncio.sleep(0)
        await i.stop_monitoring()
        assert i._monitoring_task is None
        assert task.done()
        logger.info.assert_called_with("Stopped notification monitoring")

    async def test_stop_without_task_noop(self, manager, logger):
        await make(manager, logger).stop_monitoring()
        logger.info.assert_not_called()


class TestStartupShutdown:
    async def test_startup(self, manager, logger):
        assert await make(manager, logger).send_startup_notification("proj", "1.2.3") is True
        msg = manager.send_notification.call_args[0][0]
        assert msg.title == "🚀 proj Started"
        assert "1.2.3" in msg.content
        assert msg.metadata == {"event_type": "startup", "project": "proj", "version": "1.2.3"}

    async def test_shutdown(self, manager, logger):
        manager.send_notification.return_value = False
        assert await make(manager, logger).send_shutdown_notification("proj") is False
        msg = manager.send_notification.call_args[0][0]
        assert msg.title == "🛑 proj Shutdown"
        assert msg.metadata == {"event_type": "shutdown", "project": "proj"}
