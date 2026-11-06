"""Behaviour tests for candles_feed.monitoring.http_server."""

from unittest.mock import MagicMock

import pytest
from aiohttp import web

from candles_feed.monitoring import http_server


class TestMetricsHandler:
    async def test_prometheus_unavailable(self, monkeypatch):
        monkeypatch.setattr(http_server, "PROMETHEUS_AVAILABLE", False)
        resp = await http_server.metrics_handler(MagicMock())
        assert "not available" in resp.text
        assert resp.content_type == "text/plain"

    async def test_exports_and_serves(self, monkeypatch):
        exporter, collector = MagicMock(), MagicMock()
        request = MagicMock()
        request.app = {"exporter": exporter, "collector": collector}
        monkeypatch.setattr(http_server, "PROMETHEUS_AVAILABLE", True)
        monkeypatch.setattr(http_server, "generate_latest", lambda reg: b"metric 1\n")

        resp = await http_server.metrics_handler(request)

        exporter.export_metrics.assert_called_once_with(collector)
        assert resp.body == b"metric 1\n"
        assert resp.content_type == "text/plain"

    def test_fallback_generate_latest_message(self):
        # The stub is only defined when prometheus_client is missing; verify
        # PROMETHEUS_AVAILABLE and generate_latest are consistent.
        if http_server.PROMETHEUS_AVAILABLE:
            assert http_server.REGISTRY is not None
        else:
            assert "not available" in http_server.generate_latest()


class TestStartHttpServer:
    async def test_starts_app_with_metrics_route(self, monkeypatch, capsys):
        created = {}

        class FakeRunner:
            def __init__(self, app):
                created["app"] = app

            async def setup(self):
                created["setup"] = True

        class FakeSite:
            def __init__(self, runner, host, port):
                created["site"] = (host, port)

            async def start(self):
                created["started"] = True

        monkeypatch.setattr(http_server.web, "AppRunner", FakeRunner)
        monkeypatch.setattr(http_server.web, "TCPSite", FakeSite)

        class _NoRegisterExporter(http_server.PrometheusExporter):
            def __init__(self):  # skip registering metrics in the global REGISTRY
                pass

        monkeypatch.setattr(http_server, "PrometheusExporter", _NoRegisterExporter)
        collector = MagicMock()

        runner = await http_server.start_http_server(collector, host="127.0.0.1", port=0)

        app = created["app"]
        assert isinstance(runner, FakeRunner)
        assert app["collector"] is collector
        assert isinstance(app["exporter"], _NoRegisterExporter)
        assert any(r.resource.canonical == "/metrics" for r in app.router.routes())
        assert created["site"] == ("127.0.0.1", 0)
        assert created["setup"] and created["started"]
        assert "127.0.0.1:0/metrics" in capsys.readouterr().out

    @pytest.mark.skipif(
        not http_server.PROMETHEUS_AVAILABLE, reason="prometheus_client not available"
    )
    async def test_real_server_serves_metrics(self, monkeypatch):
        # Avoid duplicate registry registration by faking the exporter.
        monkeypatch.setattr(http_server, "PrometheusExporter", MagicMock)
        monkeypatch.setattr(http_server, "generate_latest", lambda reg: b"up 1\n")
        runner = await http_server.start_http_server(MagicMock(), host="127.0.0.1", port=0)
        try:
            assert isinstance(runner, web.AppRunner)
            assert runner.addresses
        finally:
            await runner.cleanup()
