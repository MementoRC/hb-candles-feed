"""
Coinbase Advanced Trade adapter for the Candle Feed framework.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)


class CoinbaseAdvancedTradeBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Coinbase Advanced Trade exchange adapter."""

    TIMESTAMP_UNIT: str = "seconds"

    @abstractmethod
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        pass

    @abstractmethod
    def _get_ws_url(self) -> str:
        """Get WebSocket URL (internal implementation).

        :returns: WebSocket URL
        """
        pass

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return self._get_ws_url()

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT").
        :returns: Trading pair in Coinbase format (same as standard).
        """
        return trading_pair

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,  # limit is part of signature, not used by Coinbase
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param start_time: Start time in seconds.
        :param limit: Maximum number of candles to return (not used by Coinbase for this specific call).
        :returns: Dictionary of parameters for REST API request.
        """
        params: dict[str, str | int] = {
            "granularity": str(INTERVALS[interval])
        }  # granularity is string like "ONE_MINUTE"

        if start_time is not None:
            # Coinbase API expects ISO 8601 format string for start/end, or Unix epoch string.
            # convert_timestamp_to_exchange should handle this.
            params["start"] = str(self.convert_timestamp_to_exchange(start_time))

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        # Coinbase candle format:
        # {
        #   "candles": [
        #     {
        #       "start": "2022-05-15T16:00:00Z",
        #       "low": "29288.38",
        #       "high": "29477.29",
        #       "open": "29405.34",
        #       "close": "29374.47",
        #       "volume": "142.0450069"
        #     },
        #     ...
        #   ]
        # }

        candles_data: list[CandleData] = []
        if not isinstance(data, dict) or "candles" not in data:
            return candles_data

        raw_candles = data["candles"]
        if not isinstance(raw_candles, list):
            return candles_data

        for candle_item in raw_candles:
            if isinstance(candle_item, dict):
                candles_data.append(
                    CandleData(
                        timestamp_raw=self.ensure_timestamp_in_seconds(candle_item.get("start", 0)),
                        open=float(candle_item.get("open", 0)),
                        high=float(candle_item.get("high", 0)),
                        low=float(candle_item.get("low", 0)),
                        close=float(candle_item.get("close", 0)),
                        volume=float(candle_item.get("volume", 0)),
                    )
                )
        return candles_data

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
        return {
            "type": "subscribe",
            "product_ids": [trading_pair],
            "channel": "candles",
            "granularity": INTERVALS[interval],
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        # Coinbase WS candle format:
        # {
        #   "channel": "candles",
        #   "client_id": "...",
        #   "timestamp": "2023-02-14T17:02:36.346Z",
        #   "sequence_num": 1234,
        #   "events": [
        #     {
        #       "type": "candle",
        #       "candles": [
        #         {
        #           "start": "2023-02-14T17:01:00Z",
        #           "low": "22537.4",
        #           "high": "22540.7",
        #           "open": "22537.4",
        #           "close": "22540.7",
        #           "volume": "0.1360142"
        #         }
        #       ]
        #     }
        #   ]
        # }

        if data is None:
            return None

        if not isinstance(data, dict) or "events" not in data:
            return None

        ts: int = self.ensure_timestamp_in_seconds(data.get("timestamp", 0))  # type: ignore
        parsed_candles: list[CandleData] = []
        events_data = data.get("events")
        if not isinstance(events_data, list):
            return None

        for event in events_data:
            if not isinstance(event, dict) or "candles" not in event:
                continue

            candle_list_payload = event.get("candles")
            if not isinstance(candle_list_payload, list):
                continue

            for candle_payload in candle_list_payload:
                if isinstance(candle_payload, dict):
                    parsed_candles.append(
                        CandleData(
                            timestamp_raw=ts,  # Using event timestamp for all candles in the event
                            open=float(candle_payload.get("open", 0)),
                            high=float(candle_payload.get("high", 0)),
                            low=float(candle_payload.get("low", 0)),
                            close=float(candle_payload.get("close", 0)),
                            volume=float(candle_payload.get("volume", 0)),
                        )
                    )
        return parsed_candles or None

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
