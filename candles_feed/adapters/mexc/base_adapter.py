"""
Base MEXC adapter implementation for the Candle Feed framework.

This module provides a base implementation for MEXC-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)


class MEXCBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for MEXC exchange adapters.

    This class provides shared functionality for MEXC spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

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

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in MEXC format (e.g., "BTC_USDT")
        """
        return trading_pair.replace("-", "_")

    @abstractmethod
    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix.

        :returns: Kline topic prefix string
        """
        pass

    @abstractmethod
    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format.

        :param interval: Standard interval format
        :returns: Exchange-specific interval format
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        pass

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
        # Prepare the symbol in MEXC format
        symbol: str = MEXCBaseAdapter.get_trading_pair_format(trading_pair).replace("_", "").lower()
        mexc_interval: str = self.get_interval_format(interval)  # type: ignore

        return {
            "method": SUB_ENDPOINT_NAME,
            "params": [f"{self.get_kline_topic()}{mexc_interval}_{symbol}"],  # type: ignore
        }

    @abstractmethod
    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        pass

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
