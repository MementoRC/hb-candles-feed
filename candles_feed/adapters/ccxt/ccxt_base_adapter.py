"""
CCXT base adapter for the Candle Feed framework.

This module provides a base implementation for exchange adapters using CCXT.
"""

from typing import Any, Dict, List, Literal

import ccxt  # type: ignore

from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData


class CCXTBaseAdapter(BaseAdapter, SyncOnlyAdapter):
    """Base adapter for exchanges integrated via CCXT.

    This adapter uses the CCXT library to interact with exchange APIs in a
    standardized way. It implements the SyncOnlyAdapter mixin since CCXT's
    primary API is synchronous.
    """

    exchange_id: str
    market_type: Literal["spot", "perpetual", "futures"] = "spot"
    TIMESTAMP_UNIT: str = "milliseconds"

    # NoWebSocketSupportMixin methods
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")

    def parse_ws_message(self, data: Any) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")

    def __init__(self) -> None:
        """Initialize CCXT exchange instance."""
        self.exchange: ccxt.Exchange = getattr(ccxt, self.exchange_name)(
            {
                "enableRateLimit": True,
                "options": self._get_ccxt_options(),
            }
        )

    @property
    def exchange_name(self) -> str:
        """Get the CCXT exchange name.

        :returns: CCXT exchange identifier
        :raises NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("exchange_name must be defined")

    def _get_ccxt_options(self) -> dict:
        """Define CCXT-specific options.

        :returns: Dictionary of CCXT configuration options
        """
        options = {}
        if self.market_type == "perpetual":
            options = {"defaultType": "swap"}
        elif self.market_type == "futures":
            options = {"defaultType": "future"}
        else:
            options = {"defaultType": "spot"}
        return options

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to CCXT format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in CCXT format (e.g., "BTC/USDT")
        """
        return trading_pair.replace("-", "/")

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,  # Default matches AdapterProtocol.fetch_rest_candles_synchronous
    ) -> dict:
        """Get parameters for CCXT API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for CCXT API request
        """
        params: dict[str, Any] = {
            "symbol": CCXTBaseAdapter.get_trading_pair_format(trading_pair),
            "timeframe": interval,
            "since": self.convert_timestamp_to_exchange(start_time) if start_time else None,
            "limit": limit,
        }
        return params

    def _parse_rest_response(self, data: list) -> list[CandleData]:
        """Parse CCXT OHLCV response into CandleData objects.

        :param data: CCXT OHLCV response
        :returns: List of CandleData objects
        """
        candles: list[CandleData] = []
        for row in data:
            candles.append(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                    open=row[1],
                    high=row[2],
                    low=row[3],
                    close=row[4],
                    volume=row[5],
                )
            )
        return candles

    def fetch_rest_candles_synchronous(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Fetch candles using CCXT's synchronous API.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: List of CandleData objects
        """
        params = self._get_rest_params(trading_pair, interval, start_time, limit=limit)
        ohlcv = self.exchange.fetch_ohlcv(
            symbol=params["symbol"],
            timeframe=params["timeframe"],
            since=params["since"],
            limit=params["limit"],
        )
        return self._parse_rest_response(ohlcv)

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals from CCXT.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        timeframes = self.exchange.timeframes
        # Convert CCXT timeframes to seconds
        result: dict[str, int] = {}

        # Basic conversion of common timeframes
        timeframe_to_seconds = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "2h": 7200,
            "4h": 14400,
            "6h": 21600,
            "8h": 28800,
            "12h": 43200,
            "1d": 86400,
            "3d": 259200,
            "1w": 604800,
            "1M": 2592000,
        }

        for tf in timeframes:
            if tf in timeframe_to_seconds:
                result[tf] = timeframe_to_seconds[tf]

        return result
