"""
Bitget spot exchange adapter for the Candle Feed framework.
"""

from typing import Any

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_INTERVAL_TO_EXCHANGE,
    SPOT_REST_URL,
    WS_INTERVAL_TO_EXCHANGE,
    WS_INTERVALS,
    WSS_URL,
)


@ExchangeRegistry.register("bitget_spot")
class BitgetSpotAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Bitget spot exchange adapter."""

    TIMESTAMP_UNIT: str = "milliseconds"

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in Bitget spot format (e.g., "BTCUSDT")
        """
        return trading_pair.replace("-", "")

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return WSS_URL

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        params: dict[str, str | int] = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "granularity": SPOT_INTERVAL_TO_EXCHANGE.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["startTime"] = self.convert_timestamp_to_exchange(start_time)
            params["endTime"] = self.convert_timestamp_to_exchange(
                start_time + limit * INTERVALS.get(interval, 60)
            )

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Bitget spot candle format:
        [
          [
            "1639984000000",  // timestamp (ms)
            "47000.00",       // open
            "47500.00",       // high
            "46800.00",       // low
            "47200.00",       // close
            "123.456",        // volume (base asset)
            "5678.90",        // (unused field)
            "5823456.78"      // quote asset volume
          ],
          ...
        ]

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if data is None:
            return []

        # Bitget may wrap data in a "data" key or return direct array
        if isinstance(data, dict):
            candle_list = data.get("data")
            if not isinstance(candle_list, list):
                return []
        elif isinstance(data, list):
            candle_list = data
        else:
            return []

        candles: list[CandleData] = []
        for row in candle_list:
            if not isinstance(row, list) or len(row) < 8:
                continue
            candles.append(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    # row[6] is unused
                    quote_asset_volume=float(row[7]),
                )
            )
        return candles

    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles from REST API asynchronously.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Network client to use for API requests
        :returns: List of CandleData objects
        """
        return await AsyncOnlyAdapter._fetch_rest_candles(
            adapter_implementation=self,
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit,
            network_client=network_client,
        )

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :returns: WebSocket subscription payload
        """
        exchange_interval = WS_INTERVAL_TO_EXCHANGE.get(interval, interval)
        return {
            "op": "subscribe",
            "args": [
                {
                    "instType": "SPOT",
                    "channel": f"candle{exchange_interval}",
                    "instId": self.get_trading_pair_format(trading_pair),
                }
            ],
        }

    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Bitget WebSocket candle message format:
        {
          "action": "update",
          "arg": {"instType": "SPOT", "channel": "candle1m", "instId": "BTCUSDT"},
          "data": [
            ["1639984000000", "47000.00", "47500.00", "46800.00", "47200.00", "123.456", "5823456.78"]
          ]
        }

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Only process "update" action messages
        if data.get("action") != "update":
            return None

        raw_data = data.get("data")
        if not isinstance(raw_data, list) or len(raw_data) == 0:
            return None

        row = raw_data[0]
        if not isinstance(row, list) or len(row) < 7:
            return None

        return [
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6]),
            )
        ]
