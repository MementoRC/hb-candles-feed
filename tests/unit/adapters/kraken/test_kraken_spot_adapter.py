"""
Tests for the KrakenSpotAdapter using the base adapter test class.
"""

import contextlib
from datetime import datetime, timezone
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.kraken.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.kraken.spot_adapter import KrakenSpotAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestKrakenSpotAdapter(BaseAdapterTest):
    """Test suite for the KrakenSpotAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return KrakenSpotAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        base, quote = trading_pair.split("-")

        # Handle special cases
        if base == "BTC":
            base = "XBT"
        if quote == "USDT":
            quote = "USD"

        # For major currencies, Kraken adds X/Z prefix
        if base in ["XBT", "ETH", "LTC", "XMR", "XRP", "ZEC"]:
            base = f"X{base}"
        if quote in ["USD", "EUR", "GBP", "JPY", "CAD"]:
            quote = f"Z{quote}"

        return base + quote

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "pair": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, 1),  # Default to 1m
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        # Kraken only supports 'since' parameter, not 'to' or 'limit'
        params = {
            "pair": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, 1),  # Default to 1m
            "since": start_time,  # Kraken uses seconds
        }
        # Note: Kraken API ignores limit parameter, but we include it in the test
        return params

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "name": "subscribe",
            "reqid": 1,
            "pair": [self.get_expected_trading_pair_format(trading_pair)],
            "subscription": {
                "name": "ohlc",
                "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, 1),  # Default to 1m
            },
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        return {
            "error": [],
            "result": {
                "XXBTZUSD": [
                    [
                        base_time,
                        "50000.0",  # open
                        "51000.0",  # high
                        "49000.0",  # low
                        "50500.0",  # close
                        "50250.0",  # VWAP
                        "100.0",    # volume
                        158         # count
                    ],
                    [
                        base_time + 60,
                        "50500.0",  # open
                        "52000.0",  # high
                        "50000.0",  # low
                        "51500.0",  # close
                        "51000.0",  # VWAP
                        "150.0",    # volume
                        210         # count
                    ],
                ],
                "last": base_time + 120
            }
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        return [
            12345,  # channelID
            [
                str(base_time),    # start time
                str(base_time + 60),  # end time
                "50000.0",         # open
                "51000.0",         # high
                "49000.0",         # low
                "50500.0",         # close
                "50250.0",         # VWAP
                "100.0",           # volume
                158                # count
            ],
            "ohlc-1",  # channel name
            "XXBTZUSD"  # pair
        ]

    # Additional test cases specific to KrakenSpotAdapter

    def test_kraken_rest_response_structure(self, adapter):
        """Test Kraken-specific REST response structure handling."""
        # Create a custom response with Kraken's unique structure
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        response = {
            "error": [],
            "result": {
                "XXBTZUSD": [
                    [
                        base_time,
                        "50000.0",  # open
                        "51000.0",  # high
                        "49000.0",  # low
                        "50500.0",  # close
                        "50250.0",  # VWAP
                        "100.0",    # volume
                        158         # count
                    ]
                ],
                "last": base_time + 60
            }
        }

        candles = adapter._parse_rest_response(response)

        # Verify correct parsing
        assert len(candles) == 1
        candle = candles[0]

        assert candle.timestamp == base_time
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 100.0 * 50250.0  # volume * VWAP
        assert candle.n_trades == 158

    def test_kraken_trading_pair_handling(self, adapter):
        """Test Kraken's unique trading pair handling."""
        # Test various trading pair formats for Kraken

        # Test BTC/USD conversion (BTC becomes XBT, prefixed with X/Z)
        assert adapter.get_trading_pair_format("BTC-USD") == "XXBTZUSD"

        # Test BTC/USDT conversion (USDT becomes USD)
        assert adapter.get_trading_pair_format("BTC-USDT") == "XXBTZUSD"

        # Test other major currencies with prefixes
        assert adapter.get_trading_pair_format("ETH-USD") == "XETHZUSD"
        assert adapter.get_trading_pair_format("XRP-EUR") == "XXRPZEUR"

        # Test non-prefixed currencies
        assert adapter.get_trading_pair_format("DOT-USD") == "DOTZUSD"
        assert adapter.get_trading_pair_format("DOGE-USD") == "DOGEZUSD"

    def test_kraken_ws_message_parsing(self, adapter):
        """Test parsing Kraken's unique WebSocket message format."""
        # Kraken's WebSocket messages follow a specific array structure
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        ws_message = [
            42,  # channelID
            [
                str(base_time),    # start time
                str(base_time + 60),  # end time
                "50000.0",         # open
                "51000.0",         # high
                "49000.0",         # low
                "50500.0",         # close
                "50250.0",         # VWAP
                "100.0",           # volume
                158                # count
            ],
            "ohlc-1",  # channel name
            "XXBTZUSD"  # pair
        ]

        candles = adapter.parse_ws_message(ws_message)

        # Verify correct parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert abs(candle.timestamp - base_time) < 1.0  # Allow small float difference
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert abs(candle.quote_asset_volume - (100.0 * 50250.0)) < 0.1  # Allow small difference
        assert candle.n_trades == 158

    def test_timestamp_in_seconds(self, adapter):
        """Test that Kraken uses seconds for timestamps."""
        assert adapter.TIMESTAMP_UNIT == "seconds"

        # To exchange should remain in seconds
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds

    # Override the BaseAdapterTest method for async test
    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Custom test for fetch_rest_candles_async for Kraken."""
        # Skip test for SyncOnlyAdapter adapters
        with contextlib.suppress(ImportError):
            from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter
            if isinstance(adapter, SyncOnlyAdapter):
                pytest.skip("Test only applicable for async adapters")

        # Create a custom mock response
        mock_response = self.get_mock_candlestick_response()

        # Create a mock network client
        mock_client = mock.MagicMock()
        mock_client.get_rest_data = mock.AsyncMock(return_value=mock_response)

        # Call the async method
        candles = await adapter.fetch_rest_candles(trading_pair, interval, network_client=mock_client)

        # Basic validation
        assert isinstance(candles, list)
        assert all(isinstance(candle, CandleData) for candle in candles)
        assert len(candles) > 0

        # Verify the network client was called correctly
        mock_client.get_rest_data.assert_called_once()
        args, kwargs = mock_client.get_rest_data.call_args
        assert kwargs['url'] == adapter._get_rest_url()

        # For Kraken, verify at least the pair is correct without comparing entire params dict
        assert "pair" in kwargs['params']
        assert kwargs['params']["pair"] == "XXBTZUSD"  # For BTC-USDT
