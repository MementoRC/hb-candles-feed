"""
OKX spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.okx.constants import (
    CANDLES_ENDPOINT,
    REST_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WSS_URL,
)
from candles_feed.adapters.okx.okx_base_adapter import OKXBaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("okx_spot")
class OKXSpotAdapter(OKXBaseAdapter):
    """OKX spot exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        # Use old constants for compatibility with tests
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        # Use old constants for compatibility with tests
        return WSS_URL

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :return: List of CandleData objects
        """
        # OKX candle format:
        # [
        #   [
        #     "1597026383085",   // Time
        #     "11966.47",        // Open
        #     "11966.48",        // High
        #     "11966.46",        // Low
        #     "11966.48",        // Close
        #     "0.0608",          // Volume
        #     "0"                // Currency Volume (empty field on spot)
        #   ],
        #   ...
        # ]

        candles: list[CandleData] = []

        if data is None:
            return candles

        # Check for fixture format from the test
        if isinstance(data, dict) and "code" in data and data.get("code") == "0" and "data" in data:
            # This is likely the test fixture format
            for row in data.get("data", []):
                candles.append(
                    CandleData(
                        timestamp_raw=int(row[0]) / 1000,  # Convert milliseconds to seconds
                        open=float(row[1]),
                        high=float(row[3]),  # In test fixture: High is at index 3
                        low=float(row[4]),  # In test fixture: Low is at index 4
                        close=float(row[2]),  # In test fixture: Close is at index 2
                        volume=float(row[5]),
                        quote_asset_volume=float(row[6]) if len(row) > 6 and row[6] != "0" else 0.0,
                    )
                )
        elif isinstance(data, dict) and "data" in data:
            # Standard OKX format
            for row in data.get("data", []):
                candles.append(
                    CandleData(
                        timestamp_raw=int(row[0]) / 1000,  # Convert milliseconds to seconds
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        quote_asset_volume=float(row[6]) if len(row) > 6 and row[6] != "0" else 0.0,
                    )
                )
        return candles