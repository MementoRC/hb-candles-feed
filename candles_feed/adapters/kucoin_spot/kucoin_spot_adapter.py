"""
KuCoin spot exchange adapter for the Candle Feed framework.
"""

import time
from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.kucoin_spot.constants import (
    CANDLES_ENDPOINT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("kucoin_spot")
class KuCoinSpotAdapter(BaseAdapter):
    """KuCoin spot exchange adapter."""

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in KuCoin format (e.g., "BTC-USDT" - same format)
        """
        return trading_pair

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

    def get_rest_params(self,
                      trading_pair: str,
                      interval: str,
                      start_time: Optional[int] = None,
                      end_time: Optional[int] = None,
                      limit: Optional[int] = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST) -> dict:
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
        # KuCoin uses startAt and endAt parameters with unix timestamps
        params = {
            "symbol": trading_pair,
            "type": interval
        }

        if start_time:
            params["startAt"] = start_time

        if end_time:
            params["endAt"] = end_time

        if limit:
            params["limit"] = limit

        return params

    def parse_rest_response(self, data: dict) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        # KuCoin candle format:
        # [
        #   [
        #     "1630461000",     // Start time
        #     "47439.59",       // Open price
        #     "47753.47",       // High price
        #     "47358.12",       // Low price
        #     "47753.47",       // Close price
        #     "0.94554306",     // Volume
        #     "44966.21"        // Transaction amount
        #   ],
        #   ...
        # ]

        candles = []
        for row in data.get("data", []):
            candles.append(CandleData(
                timestamp_raw=int(row[0]),  # Already in seconds
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6])  # Transaction amount
            ))
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        # KuCoin requires obtaining a token first, and has a specific topic format
        # Here's the subscription format once the token is obtained
        return {
            "id": int(time.time() * 1000),
            "type": "subscribe",
            "topic": f"/market/candles:{trading_pair}_{interval}",
            "privateChannel": False,
            "response": True
        }

    def parse_ws_message(self, data: dict) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # KuCoin websocket message format:
        # {
        #   "type": "message",
        #   "topic": "/market/candles:BTC-USDT_1min",
        #   "subject": "trade.candles.update",
        #   "data": {
        #     "symbol": "BTC-USDT",
        #     "candles": [
        #       "1589970480",   // Start time
        #       "9786.8",       // Open price
        #       "9786.8",       // High price
        #       "9786.8",       // Low price
        #       "9786.8",       // Close price
        #       "0.0285",       // Volume
        #       "279.2268"      // Transaction amount
        #     ],
        #     "time": 1589970483697546000
        #   }
        # }

        if (data.get("type") == "message" and
            "data" in data and
            "candles" in data["data"]):

            candle_data = data["data"]["candles"]
            return [CandleData(
                timestamp_raw=int(candle_data[0]),  # Already in seconds
                open=float(candle_data[1]),
                high=float(candle_data[2]),
                low=float(candle_data[3]),
                close=float(candle_data[4]),
                volume=float(candle_data[5]),
                quote_asset_volume=float(candle_data[6])  # Transaction amount
            )]

        return None

    def get_supported_intervals(self) -> Dict[str, int]:
        """Get supported intervals and their durations in seconds.

        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> List[str]:
        """Get intervals supported by WebSocket API.

        Returns:
            List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
