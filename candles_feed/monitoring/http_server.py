"""HTTP server for exposing Prometheus metrics."""

from aiohttp import web
from prometheus_client import REGISTRY, generate_latest

from ..core.metrics import MetricsCollector
from .prometheus_exporter import PrometheusExporter


async def metrics_handler(request: web.Request) -> web.Response:
    """AIOHTTP handler for serving Prometheus metrics."""
    exporter: PrometheusExporter = request.app["exporter"]
    collector: MetricsCollector = request.app["collector"]

    exporter.export_metrics(collector)

    response = web.Response(body=generate_latest(REGISTRY))
    response.content_type = "text/plain; version=0.0.4"
    return response


async def start_http_server(
    collector: MetricsCollector, host: str = "0.0.0.0", port: int = 8080
) -> web.AppRunner:
    """Start an aiohttp server to expose Prometheus metrics.

    :param collector: The MetricsCollector instance to export from.
    :param host: The host to bind the server to.
    :param port: The port to bind the server to.
    :return: The aiohttp AppRunner for the server.
    """
    app = web.Application()
    app["collector"] = collector
    app["exporter"] = PrometheusExporter()
    app.router.add_get("/metrics", metrics_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"Prometheus metrics server started at http://{host}:{port}/metrics")
    return runner
