"""
Bitmart perpetual exchange adapter for the Candle Feed framework.
"""

import time
from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_REST,
    INTERVAL_TO_EXCHANGE_WS,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)


@ExchangeRegistry.register("bitmart_perpetual")
class BitmartPerpetualAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Bitmart perpetual exchange adapter."""

    TIMESTAMP_UNIT: str = "seconds"

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USD")
        :returns: Trading pair in Bitmart perpetual format (e.g., "BTCUSD")
        """
        return trading_pair.replace("-", "")

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    @override
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS

    @override
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return WSS_URL

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @override
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

        .. note::
            Bitmart perpetual API requires both ``start_time`` and ``end_time``
            to be provided together; omitting them results in a 400 Bad Request.
            When ``start_time`` is not supplied, it is calculated as
            ``now - limit * interval_seconds`` so the response covers the most
            recent *limit* candles.
        """
        interval_seconds = INTERVALS[interval]
        if start_time is None:
            start_time = int(time.time()) - limit * interval_seconds

        end_time = int(start_time) + limit * interval_seconds

        return {
            "symbol": self.get_trading_pair_format(trading_pair),
            "step": INTERVAL_TO_EXCHANGE_REST[interval],
            "start_time": int(start_time),
            "end_time": end_time,
        }

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects

        Bitmart REST response format::

            {
                "code": 1000,
                "data": [
                    {
                        "timestamp": 1631685600,
                        "open_price": "46000.00",
                        "high_price": "46500.00",
                        "low_price": "45800.00",
                        "close_price": "46200.00",
                        "volume": "100"
                    },
                    ...
                ]
            }
        """
        if data is None:
            return []

        if not isinstance(data, dict):
            return []
        candle_list = data.get("data", [])
        if not isinstance(candle_list, list):
            return []

        candles: list[CandleData] = []
        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row["timestamp"]),
                open=float(row["open_price"]),
                high=float(row["high_price"]),
                low=float(row["low_price"]),
                close=float(row["close_price"]),
                volume=float(row["volume"]),
            )
            for row in candle_list
        )
        return candles

    @override
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

    @override
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :returns: WebSocket subscription payload

        Bitmart WebSocket subscription format::

            {
                "action": "subscribe",
                "args": ["futures/klineBin1m:BTCUSD"]
            }
        """
        ws_interval = INTERVAL_TO_EXCHANGE_WS[interval]
        symbol = self.get_trading_pair_format(trading_pair)
        return {
            "action": "subscribe",
            "args": [f"futures/klineBin{ws_interval}:{symbol}"],
        }

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update

        Bitmart WebSocket message format::

            {
                "data": {
                    "items": [
                        {
                            "ts": 1631685600,
                            "o": 46000.0,
                            "h": 46500.0,
                            "l": 45800.0,
                            "c": 46200.0,
                            "v": 100.0
                        }
                    ]
                }
            }
        """
        if data is None:
            return None

        inner = data.get("data")
        if not isinstance(inner, dict):
            return None

        items = inner.get("items")
        if not isinstance(items, list):
            return None

        candles: list[CandleData] = []
        for item in items:
            if isinstance(item, dict):
                candles.append(
                    CandleData(
                        timestamp_raw=self.ensure_timestamp_in_seconds(item["ts"]),
                        open=float(item["o"]),
                        high=float(item["h"]),
                        low=float(item["l"]),
                        close=float(item["c"]),
                        volume=float(item["v"]),
                    )
                )
        return candles if candles else None
