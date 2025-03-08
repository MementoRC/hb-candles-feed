from candles_feed.adapters.gate_io.spot_adapter import GateIoSpotAdapter

from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchanges.gate_io.base_plugin import GateIoBasePlugin


class GateIoSpotPlugin(GateIoBasePlugin):
    """
    Gate.io plugin for the mock exchange server.

    This plugin implements the Gate.io Spot API for the mock server.
    """

    def __init__(self):
        """
        Initialize the Gate.io plugin.
        """
        super().__init__(ExchangeType.GATE_IO_SPOT, GateIoSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Gate.io.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v4/spot/candlesticks": ("GET", "handle_klines"),
            "/api/v4/spot/currencies/BTC": ("GET", "handle_time"),
        }