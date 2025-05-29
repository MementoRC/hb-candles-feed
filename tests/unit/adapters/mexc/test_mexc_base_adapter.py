"""
Tests for the MEXCBaseAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest import mock

import pytest

from candles_feed.adapters.mexc.base_adapter import MEXCBaseAdapter
from candles_feed.adapters.mexc.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_KLINE_TOPIC,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class ConcreteMEXCAdapter(MEXCBaseAdapter):
    """Concrete implementation of MEXCBaseAdapter for testing."""

    # MEXC spot adapter uses milliseconds
    TIMESTAMP_UNIT: str = "milliseconds"

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL."""
        return SPOT_WSS_URL

    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix."""
        return SPOT_KLINE_TOPIC

    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format."""
        return INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict:
        """Get parameters for REST API request."""
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": interval,
        }

        if limit is not None:
            params["limit"] = limit

        if start_time is not None:
            params["startTime"] = self.convert_timestamp_to_exchange(start_time)

        if end_time is not None:
            params["endTime"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects."""
        if data is None:
            return []

        candles = []

        if isinstance(data, list):
            # MEXC spot format
            for row in data:
                # MEXC spot API format:
                # [
                #   1499040000000,      // Open time
                #   "0.01634790",       // Open
                #   "0.80000000",       // High
                #   "0.01575800",       // Low
                #   "0.01577100",       // Close
                #   "148976.11427815",  // Volume
                #   1499644799999,      // Close time
                #   "2434.19055334",    // Quote asset volume
                #   308,                // Number of trades
                #   "1756.87402397",    // Taker buy base asset volume
                #   "28.46694368",      // Taker buy quote asset volume
                #   "17928899.62484339" // Ignore.
                # ]
                if len(row) >= 11:
                    timestamp = self.ensure_timestamp_in_seconds(row[0])
                    open_price = float(row[1])
                    high = float(row[2])
                    low = float(row[3])
                    close = float(row[4])
                    volume = float(row[5])
                    quote_volume = float(row[7])
                    n_trades = int(row[8]) if isinstance(row[8], (int, float, str)) else 0
                    taker_buy_base_volume = float(row[9])
                    taker_buy_quote_volume = float(row[10])

                    candles.append(
                        CandleData(
                            timestamp_raw=timestamp,
                            open=open_price,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume,
                            quote_asset_volume=quote_volume,
                            n_trades=n_trades,
                            taker_buy_base_volume=taker_buy_base_volume,
                            taker_buy_quote_volume=taker_buy_quote_volume,
                        )
                    )

        return candles

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects."""
        if data is None:
            return None

        # MEXC spot WebSocket format:
        # {
        #     "d": {
        #         "t": 1654198740000,         // time
        #         "o": "30024.53",            // open
        #         "h": "30024.53",            // high
        #         "l": "30024.52",            // low
        #         "c": "30024.52",            // close
        #         "v": "0.0413",              // volume
        #         "qv": "1240.01287",         // quote volume
        #         "n": 3                      // number of trades
        #     }
        # }

        if isinstance(data, dict) and "d" in data:
            candle_data = data["d"]

            if isinstance(candle_data, dict) and all(k in candle_data for k in ["t", "o", "h", "l", "c", "v"]):
                timestamp = self.ensure_timestamp_in_seconds(candle_data["t"])
                open_price = float(candle_data["o"])
                high = float(candle_data["h"])
                low = float(candle_data["l"])
                close = float(candle_data["c"])
                volume = float(candle_data["v"])
                quote_volume = float(candle_data.get("qv", 0))
                n_trades = int(candle_data.get("n", 0))

                return [
                    CandleData(
                        timestamp_raw=timestamp,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                        quote_asset_volume=quote_volume,
                        n_trades=n_trades,
                        taker_buy_base_volume=0.0,  # Not provided in WebSocket
                        taker_buy_quote_volume=0.0,  # Not provided in WebSocket
                    )
                ]
        return None


class TestMEXCBaseAdapter(BaseAdapterTest):
    """Test suite for the MEXCBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteMEXCAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "_")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": interval,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": interval,
            "limit": limit,
            "startTime": start_time * 1000,  # MEXC uses milliseconds
            "endTime": end_time * 1000,      # MEXC uses milliseconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        symbol = self.get_expected_trading_pair_format(trading_pair).replace("_", "").lower()
        mexc_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

        return {
            "method": SUB_ENDPOINT_NAME,
            "params": [f"{SPOT_KLINE_TOPIC}{mexc_interval}_{symbol}"],
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)  # In milliseconds

        return [
            [
                base_time,
                "50000.0",       # open
                "51000.0",       # high
                "49000.0",       # low
                "50500.0",       # close
                "100.0",         # volume
                base_time + 59999, # close time
                "5000000.0",     # quote volume
                1000,            # number of trades
                "60.0",          # taker buy base volume
                "3000000.0",     # taker buy quote volume
                "0",             # ignore
            ],
            [
                base_time + 60000,
                "50500.0",       # open
                "52000.0",       # high
                "50000.0",       # low
                "51500.0",       # close
                "150.0",         # volume
                base_time + 119999, # close time
                "7500000.0",     # quote volume
                1500,            # number of trades
                "90.0",          # taker buy base volume
                "4500000.0",     # taker buy quote volume
                "0",             # ignore
            ],
        ]

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)  # In milliseconds

        return {
            "d": {
                "t": base_time,
                "o": "50000.0",
                "h": "51000.0",
                "l": "49000.0",
                "c": "50500.0",
                "v": "100.0",
                "qv": "5000000.0",
                "n": 1000
            }
        }

    # Additional test cases specific to MEXCBaseAdapter

    def test_timestamp_in_milliseconds(self, adapter):
        """Test that timestamps are correctly handled in milliseconds."""
        assert adapter.TIMESTAMP_UNIT == "milliseconds"

        # Test timestamp conversion methods
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC

        # To exchange should convert to milliseconds
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds * 1000

        # Ensure timestamp is in seconds regardless of input format
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds * 1000) == timestamp_seconds
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds
        assert adapter.ensure_timestamp_in_seconds(str(timestamp_seconds * 1000)) == timestamp_seconds

    def test_trading_pair_format_conversion(self, adapter):
        """Test trading pair format conversion for MEXC."""
        # MEXC replaces hyphen with underscore
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC_USDT"
        assert adapter.get_trading_pair_format("ETH-BTC") == "ETH_BTC"
        assert adapter.get_trading_pair_format("SOL-USDT") == "SOL_USDT"

    def test_interval_format_conversion(self, adapter):
        """Test interval format conversion."""
        # Test different intervals
        assert adapter.get_interval_format("1m") == "Min1"
        assert adapter.get_interval_format("5m") == "Min5"
        assert adapter.get_interval_format("1h") == "Min60"
        assert adapter.get_interval_format("4h") == "Hour4"
        assert adapter.get_interval_format("1d") == "Day1"

        # Test unknown interval
        assert adapter.get_interval_format("unknown") == "unknown"

    def test_ws_subscription_topic_format(self, adapter):
        """Test WebSocket subscription topic format."""
        # Test with BTC-USDT and 1m interval
        topic = adapter.get_ws_subscription_payload("BTC-USDT", "1m")["params"][0]
        assert topic == "spot@public.kline.Min1_btcusdt"

        # Test with ETH-BTC and 1h interval
        topic = adapter.get_ws_subscription_payload("ETH-BTC", "1h")["params"][0]
        assert topic == "spot@public.kline.Min60_ethbtc"

    def test_parse_rest_response_field_mapping(self, adapter):
        """Test field mapping for REST response parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

        # Create a mock response row
        row = [
            timestamp,         # Open time
            "50000.0",         # Open
            "51000.0",         # High
            "49000.0",         # Low
            "50500.0",         # Close
            "100.0",           # Volume
            timestamp + 59999, # Close time
            "5000000.0",       # Quote asset volume
            1000,              # Number of trades
            "60.0",            # Taker buy base asset volume
            "3000000.0",       # Taker buy quote asset volume
            "0",               # Ignore
        ]

        candles = adapter._parse_rest_response([row])

        # Verify correct parsing
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping
        assert candle.timestamp == int(timestamp / 1000)  # Should be in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000
        assert candle.taker_buy_base_volume == 60.0
        assert candle.taker_buy_quote_volume == 3000000.0

    def test_parse_ws_message_field_mapping(self, adapter):
        """Test field mapping for WebSocket message parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

        # Create a mock WebSocket message
        message = {
            "d": {
                "t": timestamp,
                "o": "50000.0",
                "h": "51000.0",
                "l": "49000.0",
                "c": "50500.0",
                "v": "100.0",
                "qv": "5000000.0",
                "n": 1000
            }
        }

        candles = adapter.parse_ws_message(message)

        # Verify correct parsing
        assert candles is not None
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping
        assert candle.timestamp == int(timestamp / 1000)  # Should be in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000

    def test_kline_topic(self, adapter):
        """Test getting kline topic."""
        assert adapter.get_kline_topic() == SPOT_KLINE_TOPIC

    def test_ws_supported_intervals(self, adapter):
        """Test WebSocket supported intervals."""
        ws_intervals = adapter.get_ws_supported_intervals()
        assert ws_intervals == WS_INTERVALS

        # All intervals should be supported
        for interval in INTERVALS:
            assert interval in ws_intervals
