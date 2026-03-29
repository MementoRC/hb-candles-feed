"""
BTC Markets spot exchange adapter for the Candle Feed framework.

BTC Markets is an Australian cryptocurrency exchange. This adapter supports
REST polling only - BTC Markets does not provide a WebSocket API for candles.
"""

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter, NoWebSocketSupportMixin
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
)


@ExchangeRegistry.register("btc_markets_spot")
class BTCMarketsSpotAdapter(NoWebSocketSupportMixin, BaseAdapter, AsyncOnlyAdapter):
    """BTC Markets spot exchange adapter.

    BTC Markets uses REST polling only for candle data. The candles endpoint
    includes the market identifier in the URL path (e.g. ``/v3/markets/BTC-AUD/candles``).
    Trading pairs are passed through unchanged (e.g. ``BTC-AUD``).

    WebSocket candle streaming is not supported by BTC Markets.
    """

    TIMESTAMP_UNIT: str = "iso8601"

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to BTC Markets exchange format.

        BTC Markets uses the same hyphenated format as the candles-feed standard
        (e.g. ``BTC-AUD``) so no conversion is required.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-AUD").
        :returns: Trading pair in BTC Markets format (unchanged).
        """
        return trading_pair

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds.
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        BTC Markets does not support WebSocket candle streaming, so this
        always returns an empty list.

        :returns: Empty list as WebSocket is not supported.
        """
        return WS_INTERVALS

    def _get_rest_url(self) -> str:
        """Get the REST API base URL for candles.

        Returns the base URL without the endpoint path. The full candle URL
        (including the market identifier in the path) is constructed in
        ``fetch_rest_candles`` at request time.

        :returns: REST API base URL.
        """
        return REST_URL

    def _get_rest_url_for_pair(self, trading_pair: str) -> str:
        """Build the full REST API URL for a specific trading pair.

        BTC Markets embeds the market identifier in the URL path rather than
        passing it as a query parameter.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-AUD").
        :returns: Full REST API URL with market identifier substituted.
        """
        exchange_pair = self.get_trading_pair_format(trading_pair)
        endpoint = CANDLES_ENDPOINT.format(market_id=exchange_pair)
        return f"{REST_URL}{endpoint}"

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get query parameters for the REST API candles request.

        BTC Markets uses ``timeWindow`` for the interval and ``from`` for the
        optional start timestamp (in ISO 8601 format). The trading pair is
        embedded in the URL path rather than passed as a parameter.

        :param trading_pair: Trading pair (used for URL path, not query params).
        :param interval: Candle interval (e.g., "1m", "1h").
        :param start_time: Start time in seconds since epoch, or None for latest candles.
        :param limit: Maximum number of candles to return.
        :returns: Dictionary of query parameters for the REST API request.
        """
        params: dict[str, str | int] = {
            "timeWindow": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time is not None:
            params["from"] = str(self.convert_timestamp_to_exchange(start_time))

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        BTC Markets candles endpoint returns an array of arrays in the form::

            [
                ["2024-01-01T00:00:00.000000Z", "open", "high", "low", "close", "volume"],
                ...
            ]

        where index 0 is an ISO 8601 timestamp string and indices 1–5 are
        numeric strings for open, high, low, close, and volume respectively.

        :param data: REST API response (list of candle arrays).
        :returns: List of CandleData objects parsed from the response.
        """
        if not isinstance(data, list):
            return []

        candles: list[CandleData] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 6:
                continue

            candles.append(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
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
        """Fetch candles from the BTC Markets REST API.

        Overrides the default implementation to build the URL with the trading
        pair substituted into the path before making the request.

        :param trading_pair: Trading pair (e.g., "BTC-AUD").
        :param interval: Candle interval (e.g., "1m", "1h").
        :param start_time: Start time in seconds since epoch, or None for latest candles.
        :param limit: Maximum number of candles to return.
        :param network_client: Network client to use for API requests.
        :returns: List of CandleData objects.
        :raises ValueError: If network_client is not provided.
        """
        if network_client is None:
            raise ValueError("network_client is required for async operations")

        url = self._get_rest_url_for_pair(trading_pair)
        params = self._get_rest_params(
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit,
        )

        response = await network_client.get_rest_data(url=url, params=params)
        return self._parse_rest_response(response)

    # WebSocket methods (get_ws_url, get_ws_subscription_payload, parse_ws_message)
    # are provided by NoWebSocketSupportMixin and all raise NotImplementedError.
    #
    # AsyncOnlyAdapter provides fetch_rest_candles_synchronous() which raises
    # NotImplementedError, as this adapter is async-only.
