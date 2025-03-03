"""
AscendEx spot exchange adapter for the Candle Feed framework.
"""

from typing import Dict, List, Optional

from candles_feed.adapters.ascend_ex_spot.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_ASCENDEX_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("ascend_ex_spot")
class AscendExSpotAdapter(BaseAdapter):
    """AscendEx spot exchange adapter."""

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in AscendEx format (e.g., "BTC/USDT")
        """
        return trading_pair.replace("-", "/")

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return WSS_URL

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict:
        """Get parameters for REST API request.

        Args:
            trading_pair: Trading pair
            interval: Candle interval
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return

        Returns:
            Dictionary of parameters for REST API request
        """
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_ASCENDEX_FORMAT.get(interval, interval),
            "n": limit,
        }

        if end_time:
            params["to"] = end_time * 1000  # Convert to milliseconds

        return params

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        candles = []
        assert isinstance(data, dict), f"Unexpected data type: {type(data)}"

        for candle in data.get("data", []):
            timestamp = candle["data"]["ts"] / 1000  # Convert milliseconds to seconds
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

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        # AscendEx WebSocket subscription format
        return {
            "op": SUB_ENDPOINT_NAME,
            "ch": f"bar:{INTERVAL_TO_ASCENDEX_FORMAT.get(interval, interval)}:{self.get_trading_pair_format(trading_pair)}",
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # Handle None input
        if data is None:
            return None

        # Handle ping message - should be handled by the WebSocketStrategy class
        if data.get("m") == "ping":
            return None

        # Check if this is a candle message
        if data.get("m") == "bar" and "data" in data:
            timestamp = data["data"]["ts"] / 1000  # Convert milliseconds to seconds
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

        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        Returns:
            List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
