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

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in KuCoin format (e.g., "BTC-USDT" - same format)
        """
        return trading_pair

    @abstractmethod
    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        pass

    @abstractmethod
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        pass

    @abstractmethod
    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
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
        pass

    @abstractmethod
    def parse_rest_response(self, data: dict) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        pass

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
            "response": True,
        }

    @abstractmethod
    def parse_ws_message(self, data: Optional[dict]) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        pass

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
