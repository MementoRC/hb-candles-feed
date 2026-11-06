"""Coverage-oriented behaviour tests for candles_feed.integration.monitoring."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.integration import monitoring as mon
from candles_feed.integration.monitoring import (
    ExternalMonitoringIntegration,
    HealthCheckServer,
    MonitoringIntegrationConfig,
    PrometheusMetricsExporter,
)


@pytest.fixture
def manager():
    m = MagicMock()
    m.get_metrics.return_value = {}
    m.get_health_status.return_value = {
        "status": "healthy",
        "uptime_seconds": 100,
        "error_count": 0,
        "memory_usage_mb": 2,
    }
    return m


@pytest.fixture
def config():
    return MonitoringIntegrationConfig(prometheus_port=0, health_check_port=0)


@pytest.fixture
def logger():
    return MagicMock()


class TestPrometheusFormat:
    def test_basic_output(self, manager, config, logger):
        text = PrometheusMetricsExporter(manager, config, logger)._format_prometheus_metrics()
        assert "candles_feed_health 1" in text
        assert "candles_feed_uptime_seconds 100" in text
        assert "candles_feed_errors_total 0" in text
        assert f"candles_feed_memory_usage_bytes {2 * 1024 * 1024}" in text
        assert "request_duration_seconds" not in text

    def test_unhealthy_status(self, manager, config):
        manager.get_health_status.return_value = {"status": "degraded"}
        text = PrometheusMetricsExporter(manager, config)._format_prometheus_metrics()
        assert "candles_feed_health 0" in text

    def test_custom_metrics_with_and_without_tags(self, manager, config):
        manager.get_metrics.return_value = {
            "Foo-bar baz": [{"value": 1}, {"value": 7, "tags": {"ex": "binance", "s": "BTC"}}],
            "plain": [{"value": 3}],
            "empty": [],
        }
        text = PrometheusMetricsExporter(manager, config)._format_prometheus_metrics()
        assert 'candles_feed_foo_bar_baz{ex="binance",s="BTC"} 7' in text
        assert "candles_feed_plain 3" in text
        assert "candles_feed_empty" not in text

    def test_timing_metric_lists_are_not_emitted_as_histogram_samples(self, manager, config):
        manager.get_metrics.return_value = {"request_timing": [{"value": 0.5}]}
        text = PrometheusMetricsExporter(manager, config)._format_prometheus_metrics()
        assert "# TYPE candles_feed_request_duration_seconds histogram" in text
        assert "candles_feed_request_timing 0.5" in text


class TestPrometheusHandler:
    async def test_handler_ok(self, manager, config):
        resp = await PrometheusMetricsExporter(manager, config)._metrics_handler(MagicMock())
        assert resp.status == 200
        assert "candles_feed_health 1" in resp.text
        assert resp.content_type == "text/plain"

    async def test_handler_error_returns_500(self, manager, config, logger):
        manager.get_metrics.side_effect = RuntimeError("boom")
        resp = await PrometheusMetricsExporter(manager, config, logger)._metrics_handler(
            MagicMock()
        )
        assert resp.status == 500
        assert "Error generating metrics" in resp.text
        logger.error.assert_called_once()

    async def test_start_disabled(self, manager, logger):
        cfg = MonitoringIntegrationConfig(prometheus_enabled=False)
        exporter = PrometheusMetricsExporter(manager, cfg, logger)
        await exporter.start()
        assert exporter._runner is None
        logger.debug.assert_called_once()

    async def test_start_and_stop_real_server(self, manager, config, logger):
        exporter = PrometheusMetricsExporter(manager, config, logger)
        await exporter.start()
        assert exporter._runner is not None
        assert exporter._app is not None
        await exporter.stop()
        assert exporter._runner is None
        assert exporter._app is None

    async def test_start_failure_reraises(self, manager, config, logger, monkeypatch):
        runner = MagicMock()
        runner.setup = AsyncMock(side_effect=OSError("nope"))
        monkeypatch.setattr(mon.web, "AppRunner", lambda app: runner)
        with pytest.raises(OSError):
            await PrometheusMetricsExporter(manager, config, logger).start()
        logger.error.assert_called_once()

    async def test_stop_without_start(self, manager, config, logger):
        exporter = PrometheusMetricsExporter(manager, config, logger)
        await exporter.stop()
        logger.info.assert_called_once()


class TestHealthCheckServer:
    async def test_health_healthy(self, manager, config):
        resp = await HealthCheckServer(manager, config)._health_handler(MagicMock())
        body = json.loads(resp.text)
        assert resp.status == 200
        assert body["status"] == "healthy"
        assert body["checks"] == {"memory": "ok", "errors": "ok", "uptime": "ok"}

    async def test_health_unhealthy_warnings(self, manager, config):
        manager.get_health_status.return_value = {
            "status": "bad",
            "memory_usage_mb": 900,
            "error_count": 3,
            "uptime_seconds": 0,
        }
        resp = await HealthCheckServer(manager, config)._health_handler(MagicMock())
        body = json.loads(resp.text)
        assert resp.status == 503
        assert body["checks"] == {"memory": "warning", "errors": "warning", "uptime": "error"}

    async def test_health_exception(self, manager, config, logger):
        manager.get_health_status.side_effect = RuntimeError("x")
        resp = await HealthCheckServer(manager, config, logger)._health_handler(MagicMock())
        assert resp.status == 503
        assert json.loads(resp.text)["status"] == "error"
        logger.error.assert_called_once()

    async def test_readiness_ready(self, manager, config):
        resp = await HealthCheckServer(manager, config)._readiness_handler(MagicMock())
        assert resp.status == 200
        assert json.loads(resp.text)["ready"] is True

    @pytest.mark.parametrize(
        "uptime,errors", [(1, 0), (100, 10)], ids=["too-young", "too-many-errors"]
    )
    async def test_readiness_not_ready(self, manager, config, uptime, errors):
        manager.get_health_status.return_value = {
            "uptime_seconds": uptime,
            "error_count": errors,
        }
        resp = await HealthCheckServer(manager, config)._readiness_handler(MagicMock())
        assert resp.status == 503
        assert json.loads(resp.text)["ready"] is False

    async def test_readiness_exception(self, manager, config, logger):
        manager.get_health_status.side_effect = RuntimeError("x")
        resp = await HealthCheckServer(manager, config, logger)._readiness_handler(MagicMock())
        assert resp.status == 503
        assert "error" in json.loads(resp.text)

    async def test_liveness(self, manager, config):
        resp = await HealthCheckServer(manager, config)._liveness_handler(MagicMock())
        assert resp.status == 200
        assert json.loads(resp.text)["alive"] is True

    async def test_liveness_exception(self, manager, config, logger, monkeypatch):
        calls = {"n": 0}
        real = mon.web.json_response

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("fail")
            return real(*args, **kwargs)

        monkeypatch.setattr(mon.web, "json_response", flaky)
        resp = await HealthCheckServer(manager, config, logger)._liveness_handler(MagicMock())
        assert resp.status == 503
        assert json.loads(resp.text)["alive"] is False

    async def test_start_disabled(self, manager, logger):
        cfg = MonitoringIntegrationConfig(health_check_enabled=False)
        server = HealthCheckServer(manager, cfg, logger)
        await server.start()
        assert server._runner is None

    async def test_start_stop_registers_routes(self, manager, config, logger):
        server = HealthCheckServer(manager, config, logger)
        await server.start()
        paths = {r.resource.canonical for r in server._app.router.routes()}
        assert {"/health", "/health/readiness", "/health/liveness"} <= paths
        await server.stop()
        assert server._runner is None and server._app is None

    async def test_start_failure(self, manager, config, logger, monkeypatch):
        runner = MagicMock()
        runner.setup = AsyncMock(side_effect=OSError("nope"))
        monkeypatch.setattr(mon.web, "AppRunner", lambda app: runner)
        with pytest.raises(OSError):
            await HealthCheckServer(manager, config, logger).start()
        logger.error.assert_called_once()


class _FakeResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self, outcomes):
        self._outcomes = outcomes

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def get(self, url, timeout=None):
        outcome = self._outcomes[url]
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(outcome)


def _stop_after_first_sleep(monkeypatch, exc):
    async def fake_sleep(_):
        raise exc

    monkeypatch.setattr(mon.asyncio, "sleep", fake_sleep)


class TestExternalMonitoringIntegration:
    def test_defaults(self, manager):
        integ = ExternalMonitoringIntegration(manager)
        assert isinstance(integ.config, MonitoringIntegrationConfig)
        assert integ._monitoring_task is None

    async def test_monitor_endpoints_records_status(self, manager, logger, monkeypatch):
        cfg = MonitoringIntegrationConfig(
            external_endpoints={"ok": "http://ok", "down": "http://down", "err": "http://err"}
        )
        outcomes = {"http://ok": 200, "http://down": 500, "http://err": ConnectionError("no")}
        monkeypatch.setattr(mon.aiohttp, "ClientSession", lambda: _FakeSession(outcomes))
        _stop_after_first_sleep(monkeypatch, asyncio.CancelledError())

        integ = ExternalMonitoringIntegration(manager, cfg, logger)
        await integ._monitor_external_endpoints()

        recorded = {c.args[0]: c.args[1] for c in manager.record_metric.call_args_list}
        assert recorded == {
            "external_endpoint_ok_status": 1.0,
            "external_endpoint_down_status": 0.0,
            "external_endpoint_err_status": 0.0,
        }
        logger.warning.assert_called_once()
        logger.error.assert_called_once()

    async def test_monitor_outer_exception_then_cancel(self, manager, logger, monkeypatch):
        cfg = MonitoringIntegrationConfig()
        # 1st sleep (in try) fails -> handler logs, sleeps again (ok) -> next loop sleep cancels.
        seq = [RuntimeError("sleep failed"), None, asyncio.CancelledError()]

        async def fake_sleep(_):
            exc = seq.pop(0)
            if exc is not None:
                raise exc

        monkeypatch.setattr(mon.asyncio, "sleep", fake_sleep)
        await ExternalMonitoringIntegration(manager, cfg, logger)._monitor_external_endpoints()
        logger.error.assert_called_once()
        assert "Error in external endpoint monitoring" in logger.error.call_args.args[0]

    async def test_start_stop_with_endpoints(self, manager, logger, monkeypatch):
        cfg = MonitoringIntegrationConfig(
            prometheus_port=0, health_check_port=0, external_endpoints={"a": "http://a"}
        )
        integ = ExternalMonitoringIntegration(manager, cfg, logger)
        monkeypatch.setattr(integ, "_monitor_external_endpoints", lambda: asyncio.sleep(10))
        await integ.start()
        assert integ._monitoring_task is not None
        await integ.stop()
        assert integ._monitoring_task is None
        assert integ.prometheus_exporter._runner is None
        assert integ.health_check_server._runner is None

    async def test_start_without_endpoints_creates_no_task(self, manager, config, logger):
        integ = ExternalMonitoringIntegration(manager, config, logger)
        await integ.start()
        assert integ._monitoring_task is None
        await integ.stop()

    async def test_start_failure_stops_and_reraises(self, manager, config, logger):
        integ = ExternalMonitoringIntegration(manager, config, logger)
        integ.prometheus_exporter.start = AsyncMock(side_effect=RuntimeError("fail"))
        integ.stop = AsyncMock()
        with pytest.raises(RuntimeError):
            await integ.start()
        integ.stop.assert_awaited_once()
