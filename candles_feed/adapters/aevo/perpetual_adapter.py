"""
Aevo perpetual exchange adapter for the Candle Feed framework.

Aevo is a perpetuals-only exchange. The mark-history endpoint returns mark
price data (not OHLCV), so open/high/low/close are all set to the mark price
and volume is set to 0.0.
"""

from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)

# Nanoseconds divisor: Aevo timestamps are in nanoseconds
_NS_TO_SECONDS: int = 1_000_000_000


@ExchangeRegistry.register("aevo_perpetual")
class AevoPerpetualAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Aevo perpetual exchange adapter.

    Aevo only provides mark price history (not full OHLCV). All OHLC fields
    are populated with the mark price, and volume is set to 0.0.

    REST timestamp parameters are in nanoseconds; response timestamps are also
    in nanoseconds and are converted to seconds for CandleData storage.

    WebSocket uses a ticker channel at 500 ms granularity; the mark_price from
    ticker messages is used to construct synthetic candles.
    """

    @override
    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to Aevo instrument name.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDC")
        :returns: Aevo instrument name (e.g., "BTC-PERP")
        """
        base, _ = trading_pair.split("-", 1)
        return f"{base}-PERP"

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    @override
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return self._get_ws_url()

    @override
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS

    @override
    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for the mark-history endpoint.

        :returns: Full REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return WSS_URL

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for the REST API request.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDC")
        :param interval: Candle interval (e.g., "1m")
        :param start_time: Start time in seconds (will be converted to nanoseconds)
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for the REST API request
        """
        instrument_name = AevoPerpetualAdapter.get_trading_pair_format(trading_pair)
        resolution = INTERVAL_TO_EXCHANGE.get(interval, INTERVALS.get(interval, 60))

        params: dict[str, str | int] = {
            "instrument_name": instrument_name,
            "resolution": resolution,
            "limit": limit,
        }

        if start_time is not None:
            params["start_timestamp"] = start_time * _NS_TO_SECONDS

        return params

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse the REST API response into CandleData objects.

        Aevo returns: {"history": [[timestamp_ns, price], ...]}

        Since only mark price is provided, open/high/low/close are all set to
        that price and volume is 0.0.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if data is None or not isinstance(data, dict):
            return []

        history = data.get("history")
        if not history or not isinstance(history, list):
            return []

        candles: list[CandleData] = []
        for entry in history:
            if not isinstance(entry, list) or len(entry) < 2:
                continue

            timestamp_ns = int(entry[0])
            timestamp_s = timestamp_ns // _NS_TO_SECONDS
            price = float(entry[1])

            candles.append(
                CandleData(
                    timestamp_raw=timestamp_s,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=0.0,
                    quote_asset_volume=0.0,
                    n_trades=0,
                    taker_buy_base_volume=0.0,
                    taker_buy_quote_volume=0.0,
                )
            )

        return candles

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles from the REST API asynchronously.

        :param trading_pair: Trading pair in standard format
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

    @override
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get the WebSocket subscription payload.

        Subscribes to the 500 ms ticker channel for the given instrument.
        Aevo does not provide a candlestick WebSocket channel; the ticker
        channel is used as a mark price feed.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDC")
        :param interval: Candle interval (acknowledged but not sent to exchange)
        :returns: WebSocket subscription payload
        """
        instrument_name = AevoPerpetualAdapter.get_trading_pair_format(trading_pair)
        return {
            "op": "subscribe",
            "data": [f"ticker-500ms:{instrument_name}"],
        }

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse a WebSocket message into CandleData objects.

        Expects Aevo ticker messages of the form:
        {"type": "update", "channel": "ticker-500ms:BTC-PERP",
         "data": {"mark_price": "50000.0", ...}}

        Since Aevo tickers carry only mark price, all OHLC fields are set to
        the mark_price and volume is 0.0. The timestamp is taken from wall
        time via the message's ``timestamp`` field (nanoseconds) when present,
        or the current exchange time.

        :param data: WebSocket message dictionary
        :returns: List with a single CandleData, or None if not a ticker update
        """
        if data is None:
            return None

        channel: str = data.get("channel", "")
        if not channel.startswith("ticker-500ms:"):
            return None

        ticker_data = data.get("data")
        if not isinstance(ticker_data, dict):
            return None

        mark_price_raw = ticker_data.get("mark_price")
        if mark_price_raw is None:
            return None

        price = float(mark_price_raw)

        # Prefer the message-level timestamp (nanoseconds); fall back to data-level
        raw_ts = data.get("timestamp") or ticker_data.get("timestamp")
        if raw_ts is not None:
            timestamp_s = int(raw_ts) // _NS_TO_SECONDS
        else:
            # Use ensure_timestamp_in_seconds with None to get current time
            timestamp_s = self.ensure_timestamp_in_seconds(None)

        return [
            CandleData(
                timestamp_raw=timestamp_s,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0.0,
                quote_asset_volume=0.0,
                n_trades=0,
                taker_buy_base_volume=0.0,
                taker_buy_quote_volume=0.0,
            )
        ]
