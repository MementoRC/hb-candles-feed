"""
Base KuCoin adapter implementation for the Candle Feed framework.

This module provides a base implementation for KuCoin-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

import time
from abc import abstractmethod
from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.kucoin.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class KuCoinBaseAdapter(BaseAdapter):
    """Base class for KuCoin exchange adapters.

    This class provides shared functionality for KuCoin spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :return: Trading pair in KuCoin format (e.g., "BTC-USDT" - same format)
        """
        return trading_pair

    @abstractmethod
    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        pass

    @abstractmethod
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        pass

    @abstractmethod
    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :param limit: Maximum number of candles to return
        :return: Dictionary of parameters for REST API request
        """
        pass

    @abstractmethod
    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :return: List of CandleData objects
        """
        pass

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :return: WebSocket subscription payload
        """
        # KuCoin requires obtaining a token first, and has a specific topic format
        # Here's the subscription format once the token is obtained
        return {
            "id": int(time.time() * 1000),
            "type": "subscribe",
            "topic": f"/market/candles:{trading_pair}_{interval}",
            "privateChannel": False,
            "response": True,
        }

    @abstractmethod
    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :return: List of CandleData objects or None if message is not a candle update
        """
        pass

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :return: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :return: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
