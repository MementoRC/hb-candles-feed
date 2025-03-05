"""
Exchange plugin interface for the mock exchange server.
"""

import abc
from typing import Any

from aiohttp import web

from candles_feed.core.candle_data import CandleData
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType


class ExchangePlugin(abc.ABC):
    """
    Base class for exchange-specific plugins for the mock server.

    This abstract class defines the interface that all exchange plugins must implement.
    Each exchange adapter needs a corresponding plugin to translate between the
    standardized mock server format and the exchange-specific formats.
    """

    def __init__(self, exchange_type: ExchangeType):
        """
        Initialize the exchange plugin.

        :param exchange_type: The type of exchange this plugin handles.
        """
        self.exchange_type = exchange_type

    @property
    @abc.abstractmethod
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for this exchange.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
            Example: {'/api/v3/klines': ('GET', 'handle_klines')}.
        """
        pass

    @property
    @abc.abstractmethod
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for this exchange.

        :returns: A dictionary mapping URL paths to handler names.
            Example: {'/ws': 'handle_websocket'}.
        """
        pass

    @abc.abstractmethod
    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> Any:
        """
        Format candle data as a REST API response for this exchange.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from the exchange's REST API.
        """
        pass

    @abc.abstractmethod
    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> Any:
        """
        Format candle data as a WebSocket message for this exchange.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from the exchange's WebSocket API.
        """
        pass

    @abc.abstractmethod
    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        pass

    @abc.abstractmethod
    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        pass

    @abc.abstractmethod
    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        pass

    @abc.abstractmethod
    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names
            (symbol, interval, start_time, end_time, limit).
        """
        pass

    def normalize_trading_pair(self, trading_pair: str) -> str:
        """
        Normalize a trading pair to a standard format.

        :param trading_pair: The trading pair in exchange-specific format.
        :returns: The trading pair in standard format.
        """
        # Default implementation (might be overridden by specific exchanges)
        return trading_pair.upper()

    def translate_interval(self, interval: str, to_exchange: bool = True) -> str:
        """
        Translate between standard interval format and exchange-specific format.

        :param interval: The interval to translate.
        :param to_exchange: If True, translate from standard to exchange format.
            If False, translate from exchange to standard format.
        :returns: The translated interval.
        """
        # Default implementation (can be overridden by specific exchanges)
        return interval
