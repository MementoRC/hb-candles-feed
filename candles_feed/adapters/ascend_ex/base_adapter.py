"""
AscendEx spot exchange adapter for the Candle Feed framework.
"""
from abc import abstractmethod

from candles_feed.adapters.ascend_ex.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData


class AscendExBaseAdapter(BaseAdapter):
    """AscendEx spot exchange adapter."""

    TIMESTAMP_UNIT: str = "milliseconds"

    @staticmethod
    @abstractmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        pass

    @staticmethod
    @abstractmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

       :returns: WebSocket URL.
        """
        pass

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT").
        :returns: Trading pair in AscendEx format (e.g., "BTC/USDT").
        """
        return trading_pair.replace("-", "/")

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to return.
        :returns: Dictionary of parameters for REST API request.
        """
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "n": limit,
        }

        if end_time:
            params["to"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response.
        :returns: List of CandleData objects.
        """
        candles = []
        assert isinstance(data, dict), f"Unexpected data type: {type(data)}"

        for candle in data.get("data", []):
            timestamp = self.ensure_timestamp_in_seconds(candle["data"]["ts"])
            candles.append(
                CandleData(
                    timestamp_raw=timestamp,
                    open=float(candle["data"]["o"]),
                    high=float(candle["data"]["h"]),
                    low=float(candle["data"]["l"]),
                    close=float(candle["data"]["c"]),
                    volume=0.0,  # No volume data available
                    quote_asset_volume=float(candle["data"]["v"]),
                    n_trades=0,  # No trade count data available
                    taker_buy_base_volume=0.0,  # No taker data available
                    taker_buy_quote_volume=0.0,  # No taker data available
                )
            )
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :returns: WebSocket subscription payload.
        """
        # AscendEx WebSocket subscription format
        return {
            "op": SUB_ENDPOINT_NAME,
            "ch": f"bar:{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}:{self.get_trading_pair_format(trading_pair)}",
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message.
        :returns: List of CandleData objects or None if message is not a candle update.
        """
        # Handle None input
        if data is None:
            return None

        # Handle ping message - should be handled by the WebSocketStrategy class
        if data.get("m") == "ping":
            return None

        # Check if this is a candle message
        if data.get("m") == "bar" and "data" in data:
            timestamp = self.ensure_timestamp_in_seconds(data["data"]["ts"])
            return [
                CandleData(
                    timestamp_raw=timestamp,
                    open=float(data["data"]["o"]),
                    high=float(data["data"]["h"]),
                    low=float(data["data"]["l"]),
                    close=float(data["data"]["c"]),
                    volume=0.0,  # No volume data available
                    quote_asset_volume=float(data["data"]["v"]),
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
