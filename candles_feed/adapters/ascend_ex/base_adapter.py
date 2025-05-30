"""
AscendEx spot exchange adapter for the Candle Feed framework.
"""

from abc import abstractmethod
from typing import List

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)


class AscendExBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for Binance exchange adapters.

    This class provides shared functionality for AscendEx spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    TIMESTAMP_UNIT: str = "milliseconds"

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

        :returns: WebSocket URL.
        """
        return self._get_ws_url()

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT").
        :returns: Trading pair in AscendEx format (e.g., "BTC/USDT").
        """
        return trading_pair.replace("-", "/")

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param start_time: Start time in seconds.
        :param limit: Maximum number of candles to return.
        :returns: Dictionary of parameters for REST API request.
        """
        params: dict[str, str | int] = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "n": limit,
        }

        # AscendEx uses 'to' for end time, but _fetch_rest_candles doesn't pass end_time.
        # If start_time is provided, AscendEx API might implicitly fetch from start_time onwards.
        # The 'from' parameter (for start_time) is also supported by AscendEx.
        if start_time:
            params["from"] = self.convert_timestamp_to_exchange(start_time)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response.
        :returns: List of CandleData objects.
        """
        # AcsendEx REST API response format
        # {
        #     "status": "ok",
        #     "data": [
        #         {
        #             "data": {
        #                 "ts": 1626835200000,
        #                 "o": "0.0",
        #                 "h": "0.0",
        #                 "l": "0.0",
        #                 "c": "0.0",
        #                 "v": "0.0"
        #             }
        #         }
        #     ]
        # }

        if data is None:
            return []

        candles: list[CandleData] = []
        assert isinstance(data, dict), f"Unexpected data type: {type(data)}"

        for candle_item in data.get("data", []):
            assert isinstance(candle_item, dict)
            candle_payload = candle_item.get("data")
            assert isinstance(candle_payload, dict)

            timestamp = self.ensure_timestamp_in_seconds(candle_payload["ts"])
            # timestamp = self.ensure_timestamp_in_seconds(candle["data"]["ts"]) # Erroneous duplicate line removed
            candles.append(
                CandleData(
                    timestamp_raw=timestamp,
                    open=float(candle_payload["o"]),  # Corrected to candle_payload
                    high=float(candle_payload["h"]),  # Corrected to candle_payload
                    low=float(candle_payload["l"]),  # Corrected to candle_payload
                    close=float(candle_payload["c"]),  # Corrected to candle_payload
                    volume=0.0,  # No volume data available
                    quote_asset_volume=float(candle_payload["v"]),  # Corrected to candle_payload
                    n_trades=0,  # No trade count data available
                    taker_buy_base_volume=0.0,  # No taker data available
                    taker_buy_quote_volume=0.0,  # No taker data available
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

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :returns: WebSocket subscription payload.
        """
        return {
            "op": SUB_ENDPOINT_NAME,
            "ch": f"bar:{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}:{self.get_trading_pair_format(trading_pair)}",
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message.
        :returns: List of CandleData objects or None if message is not a candle update.
        """
        # AscendEx WebSocket API message format
        # {
        #     "m": "bar",
        #     "data": {
        #         "ts": 1626835200000,
        #         "o": "0.0",
        #         "h": "0.0",
        #         "l": "0.0",
        #         "c": "0.0",
        #         "v": "0.0"
        #     }
        # }

        if data is None:
            return None

        # Handle ping message - should be handled by the WebSocketStrategy class
        if data.get("m") == "ping":
            return None

        # Check if this is a candle message
        if data.get("m") == "bar" and "data" in data:
            candle_payload = data["data"]
            assert isinstance(candle_payload, dict)
            timestamp = self.ensure_timestamp_in_seconds(candle_payload["ts"])
            return [
                CandleData(
                    timestamp_raw=timestamp,
                    open=float(candle_payload["o"]),
                    high=float(candle_payload["h"]),
                    low=float(candle_payload["l"]),
                    close=float(candle_payload["c"]),
                    volume=0.0,  # No volume data available
                    quote_asset_volume=float(candle_payload["v"]),
                    n_trades=0,  # No trade count data available
                    taker_buy_base_volume=0.0,  # No taker data available
                    taker_buy_quote_volume=0.0,  # No taker data available
                )
            ]
        return None

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds.
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API.
        """
        return WS_INTERVALS
