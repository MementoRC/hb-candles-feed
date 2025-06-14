"""
Base Gate.io adapter implementation for the Candle Feed framework.

This module provides a base implementation for Gate.io-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)


class GateIoBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for Gate.io exchange adapters.

    This class provides shared functionality for Gate.io spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

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

    @abstractmethod
    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :returns: Channel name string
        """
        pass

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in Gate.io format (e.g., "BTC_USDT")
        """
        return trading_pair.replace("-", "_")

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
        params: dict[str, str | int] = {  # type: ignore
            "currency_pair": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["from"] = self.convert_timestamp_to_exchange(start_time)  # type: ignore

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        # Gate.io candle format:
        # [
        #   [
        #     "1626770400",  // timestamp
        #     "29932.21",    // open
        #     "30326.37",    // close
        #     "29586.26",    // low
        #     "30549.57",    // high
        #     "2501.976433", // volume
        #     "74626209.16", // quote currency volume
        #     "BTC_USDT"     // currency pair
        #   ],
        #   ...
        # ]

        if data is None:
            return []

        candles: list[CandleData] = []
        if not isinstance(data, list):  # Gate.io returns a list of lists
            return candles

        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                open=float(row[1]),
                high=float(row[4]),  # Gate.io has high at index 4
                low=float(row[3]),  # Gate.io has low at index 3
                close=float(row[2]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6]),
                n_trades=0,  # No trade count data available
                taker_buy_base_volume=0.0,  # No taker data available
                taker_buy_quote_volume=0.0,  # No taker data available
            )
            for row in data
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
        return {
            "method": "subscribe",
            "params": [
                f"{self.get_channel_name()}",
                {
                    "currency_pair": self.get_trading_pair_format(trading_pair),
                    "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
                },
            ],
            "id": 12345,
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        # Gate.io WS candle format (similar to REST format):
        # [
        #   "1626770400",  // timestamp
        #   "29932.21",    // open
        #   "30326.37",    // close
        #   "29586.26",    // low
        #   "30549.57",    // high
        #   "2501.976433", // volume
        #   "74626209.16", // quote currency volume
        #   "BTC_USDT"     // currency pair
        # ]
        if data is None:
            return None

        if (
            isinstance(data, dict)
            and data.get("method") == "update"
            and data.get("channel") == self.get_channel_name()  # type: ignore
        ):
            params_data = data.get("params")
            if not isinstance(params_data, list) or len(params_data) < 2:
                return None

            candle_payload = params_data[1]
            if not isinstance(candle_payload, list) or len(candle_payload) < 7:
                return None

            return [
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(candle_payload[0]),
                    open=float(candle_payload[1]),
                    high=float(candle_payload[4]),  # Gate.io has high at index 4
                    low=float(candle_payload[3]),  # Gate.io has low at index 3
                    close=float(candle_payload[2]),
                    volume=float(candle_payload[5]),
                    quote_asset_volume=float(candle_payload[6]),
                    n_trades=0,  # No trade count data available
                    taker_buy_base_volume=0.0,  # No taker data available
                    taker_buy_quote_volume=0.0,  # No taker data available
                )
            ]
        return None

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
