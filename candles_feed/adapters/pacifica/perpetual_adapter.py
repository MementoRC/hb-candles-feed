"""
Pacifica perpetual exchange adapter for the Candle Feed framework.
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
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)


@ExchangeRegistry.register("pacifica_perpetual")
class PacificaPerpetualAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Pacifica perpetual exchange adapter.

    Pacifica is a perpetual futures exchange. This adapter handles candle data
    retrieval via REST and WebSocket using the Pacifica API.

    Trading pair format: "BTC-USDC" -> "BTC" (base asset only, split on dash).
    Timestamps: milliseconds.
    """

    TIMESTAMP_UNIT: str = "milliseconds"

    @override
    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDC")
        :returns: Trading pair in Pacifica format (e.g., "BTC")
        """
        base, _ = trading_pair.split("-", 1)
        return base

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    @override
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return self._get_ws_url()

    @override
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @override
    def _get_ws_url(self) -> str:
        """Get WebSocket URL (internal implementation).

        :returns: WebSocket URL
        """
        return WSS_URL

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        Pacifica requires both start_time and end_time in milliseconds.
        If start_time is not provided, it is computed as now - (limit * interval_seconds).

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds (optional; defaults to now - limit*interval)
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        symbol: str = self.get_trading_pair_format(trading_pair)
        exchange_interval: str = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        interval_seconds: int = INTERVALS.get(interval, 60)

        now_ms: int = int(time.time() * 1000)

        if start_time is not None:
            start_ms: int = int(self.convert_timestamp_to_exchange(start_time))
        else:
            start_ms = now_ms - limit * interval_seconds * 1000

        end_ms: int = start_ms + limit * interval_seconds * 1000

        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": exchange_interval,
            "start_time": start_ms,
            "end_time": end_ms,
            "limit": limit,
        }

        return params

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Pacifica REST response format:
        {
          "success": true,
          "data": [
            {
              "t": <timestamp_ms>,
              "o": <open>,
              "h": <high>,
              "l": <low>,
              "c": <close>,
              "v": <volume>,
              "n": <n_trades>,
              "T": <end_time_ms>,
              "s": <symbol>,
              "i": <interval>
            },
            ...
          ]
        }

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if data is None:
            return []

        if isinstance(data, dict):
            candle_list = data.get("data")
        elif isinstance(data, list):
            candle_list = data
        else:
            return []

        if not candle_list or not isinstance(candle_list, list):
            return []

        candles: list[CandleData] = []
        for row in candle_list:
            if not isinstance(row, dict):
                continue
            candles.append(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(row["t"]),
                    open=float(row["o"]),
                    high=float(row["h"]),
                    low=float(row["l"]),
                    close=float(row["c"]),
                    volume=float(row["v"]),
                    quote_asset_volume=0.0,
                    n_trades=int(row.get("n", 0)),
                    taker_buy_base_volume=0.0,
                    taker_buy_quote_volume=0.0,
                )
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
        """
        pair: str = self.get_trading_pair_format(trading_pair)
        exchange_interval: str = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

        return {
            "method": "subscribe",
            "params": {
                "source": "candle",
                "symbol": pair,
                "interval": exchange_interval,
            },
        }

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Pacifica WebSocket candle message format matches the REST data format:
        {
          "t": <timestamp_ms>,
          "o": <open>,
          "h": <high>,
          "l": <low>,
          "c": <close>,
          "v": <volume>,
          "n": <n_trades>,
          "T": <end_time_ms>,
          "s": <symbol>,
          "i": <interval>
        }

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Candle messages carry the "t" (timestamp) field directly
        if "t" not in data or "o" not in data:
            return None

        return [
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(data["t"]),
                open=float(data["o"]),
                high=float(data["h"]),
                low=float(data["l"]),
                close=float(data["c"]),
                volume=float(data["v"]),
                quote_asset_volume=0.0,
                n_trades=int(data.get("n", 0)),
                taker_buy_base_volume=0.0,
                taker_buy_quote_volume=0.0,
            )
        ]
