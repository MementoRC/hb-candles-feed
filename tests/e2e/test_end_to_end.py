"""
End-to-end test for the Candles Feed framework.

This module demonstrates how to use the exchange simulation framework
to test the Candles Feed in a realistic but controlled environment.
"""

import asyncio
import logging
import re
from urllib.parse import urlparse, urlunparse

import aiohttp
import pytest
from aioresponses import aioresponses

from candles_feed.adapters.binance import constants as binance_constants  # For REAL URLs
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.factory import get_plugin
from candles_feed.mocking_resources.core.server import MockedExchangeServer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEndToEnd:
    """End-to-end test suite for the Candles Feed."""

    @pytest.fixture
    async def aioresponses_mock_binance_server(self, unused_tcp_port):
        """Create a mock Binance server for testing, with aioresponses intercepting calls."""
        plugin = get_plugin(ExchangeType.BINANCE_SPOT)
        host = "127.0.0.1"  # Use 127.0.0.1 explicitly
        port = unused_tcp_port

        server = MockedExchangeServer(plugin, host, port)

        # Add trading pairs to the mock server
        # These need to match what the test will request
        server.add_trading_pair("BTC-USDT", "1m", initial_price=50000.0)
        server.add_trading_pair("ETH-USDT", "1m", initial_price=3000.0)

        # Ensure the server generates some initial candles for these pairs
        # The add_trading_pair method in MockedExchangeServer already does this.

        await server.start()

        server.mock_rest_url_base = f"http://{host}:{port}"

        # For Binance Spot, the WebSocket path is typically /ws or part of a stream path
        # The BinanceSpotPlugin inherits ws_routes from BinanceBasePlugin which is {"/ws": "handle_websocket"}
        ws_path = "/ws"  # Default for Binance Spot based on BinanceBasePlugin
        server.mock_ws_url = f"ws://{host}:{port}{ws_path}"

        async def make_passthrough_callback(
            target_url_base_for_mock_server, original_request_method
        ):
            async def callback(url_obj, **kwargs):  # url_obj is yarl.URL from aioresponses
                # Construct the final target URL for the local mock server
                # url_obj.path and url_obj.query_string are from the *intercepted* request.
                # target_url_base_for_mock_server is like "http://127.0.0.1:xxxx"

                final_target_url = urlunparse(
                    (
                        urlparse(target_url_base_for_mock_server).scheme,
                        urlparse(target_url_base_for_mock_server).netloc,
                        url_obj.path,  # Use path from the intercepted URL
                        "",  # params for urlunparse
                        url_obj.query_string,  # Use query string from the intercepted URL
                        "",  # fragment for urlunparse
                    )
                )

                request_headers = {}
                if kwargs.get("headers"):
                    request_headers = {
                        k: v
                        for k, v in kwargs["headers"].items()
                        if k.lower() not in ["host", "content-length", "transfer-encoding"]
                    }

                outgoing_json_payload = kwargs.get(
                    "json"
                )  # aioresponses uses 'json' not 'json_payload'
                outgoing_data = kwargs.get("data")

                if outgoing_json_payload is not None and outgoing_data is not None:
                    # Prefer JSON if both are somehow provided, though typically only one is.
                    outgoing_data = None

                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.request(
                            original_request_method,
                            final_target_url,
                            data=outgoing_data,
                            json=outgoing_json_payload,
                            headers=request_headers,
                            allow_redirects=kwargs.get("allow_redirects", True),
                        ) as resp:
                            content = await resp.read()
                            response_headers = {
                                k: v
                                for k, v in resp.headers.items()
                                if k.lower()
                                not in [
                                    "transfer-encoding",
                                    "content-length",
                                ]  # content-length might mismatch if content changes
                            }
                            # If content is JSON, aioresponses might try to re-serialize it.
                            # It's often safer to pass content as bytes (body).
                            return aioresponses.CallbackResult(
                                status=resp.status, body=content, headers=response_headers
                            )
                    except aiohttp.ClientConnectorError as e:
                        logger.error(f"Passthrough to {final_target_url} failed: {e}")
                        return aioresponses.CallbackResult(
                            status=503, body=f"Mock server connection error: {e}"
                        )

            return callback

        with aioresponses() as m:
            real_binance_spot_base_url = (
                binance_constants.SPOT_REST_URL
            )  # "https://api.binance.com"

            # Intercept all routes defined in the plugin
            for route_path, (method, _) in plugin.rest_routes.items():
                real_url_to_intercept_pattern = re.compile(
                    f"^{re.escape(real_binance_spot_base_url + route_path)}(\\?.*)?$"
                )

                # The passthrough callback will use server.mock_rest_url_base and the path from the intercepted URL
                m.add(
                    real_url_to_intercept_pattern,
                    method=method.upper(),
                    callback=await make_passthrough_callback(
                        server.mock_rest_url_base, method.upper()
                    ),
                    repeat=True,
                )

            yield server  # Provide the MockedExchangeServer instance to the test

        # Teardown: stop the server
        await server.stop()

    @pytest.mark.asyncio
    async def test_rest_candles_retrieval(self, aioresponses_mock_binance_server):
        """Test retrieving candles via REST API using aioresponses."""
        # Create a CandlesFeed instance
        feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        try:
            # Fetch historical candles
            logger.info("Fetching candles via REST API...")
            candles = await feed.fetch_candles()

            # Verify candles were received
            assert len(candles) > 0, "No candles received"
            logger.info(
                f"Successfully received {len(candles)} candles via aioresponses-intercepted REST"
            )

            # Convert to DataFrame for easier inspection
            df = feed.get_candles_df()
            logger.info(f"First candle: {df.iloc[0].to_dict()}")
            logger.info(f"Last candle: {df.iloc[-1].to_dict()}")

            # Verify candle data looks reasonable
            assert all(df["open"] > 0), "Open prices should be positive"
            assert all(df["high"] >= df["open"]), "High should be >= open"
            assert all(df["low"] <= df["open"]), "Low should be <= open"
            assert all(df["volume"] > 0), "Volume should be positive"

        finally:
            # Clean up resources
            await feed.stop()

    @pytest.mark.asyncio
    async def test_multiple_trading_pairs(self, aioresponses_mock_binance_server):
        """Test working with multiple trading pairs simultaneously."""
        # Create feeds for different trading pairs
        btc_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        eth_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="ETH-USDT", interval="1m", max_records=100
        )

        try:
            # Fetch historical data for both feeds
            await asyncio.gather(btc_feed.fetch_candles(), eth_feed.fetch_candles())

            # Verify candles were received for each feed
            assert len(btc_feed.get_candles()) > 0, "No BTC candles received"
            assert len(eth_feed.get_candles()) > 0, "No ETH candles received"

            # Compare prices to ensure they're different (as expected for different assets)
            btc_price = btc_feed.get_candles()[-1].close
            eth_price = eth_feed.get_candles()[-1].close

            logger.info(f"Latest prices via aioresponses - BTC: {btc_price}, ETH: {eth_price}")

            # Prices should be in different ranges based on our mock server configuration
            assert 35000 < btc_price < 65000, "BTC price should be somewhere around 50000"
            assert 1500 < eth_price < 4500, "ETH price should be somewhere around 3000"

        finally:
            # Clean up resources
            await asyncio.gather(btc_feed.stop(), eth_feed.stop())


if __name__ == "__main__":
    # This allows running the test directly
    pytest.main(["-xvs", __file__])
