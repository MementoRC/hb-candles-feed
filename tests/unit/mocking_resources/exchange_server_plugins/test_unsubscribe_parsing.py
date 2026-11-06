"""
Regression tests: unsubscribe messages must parse to the same (pair, interval) tuples as subscribe.

The server routes both verbs through ``plugin.parse_ws_subscription``, so a SUBSCRIBE-only
parser silently turns every unsubscribe into a no-op.
"""

import pytest

from candles_feed.mocking_resources.exchange_server_plugins.ascend_ex.spot_plugin import (
    AscendExSpotPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.bybit.spot_plugin import (
    BybitSpotPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.coinbase_advanced_trade.spot_plugin import (
    CoinbaseAdvancedTradeSpotPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.gate_io.spot_plugin import (
    GateIoSpotPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.perpetual_plugin import (
    HyperliquidPerpetualPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.kraken.spot_plugin import (
    KrakenSpotPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.kucoin.spot_plugin import (
    KucoinSpotPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.okx.spot_plugin import OKXSpotPlugin

CASES = [
    (
        OKXSpotPlugin,
        {"op": "subscribe", "args": [{"channel": "candle1m", "instId": "BTC-USDT"}]},
        {"op": "unsubscribe", "args": [{"channel": "candle1m", "instId": "BTC-USDT"}]},
    ),
    (
        BybitSpotPlugin,
        {"op": "subscribe", "args": ["kline.1.BTCUSDT"]},
        {"op": "unsubscribe", "args": ["kline.1.BTCUSDT"]},
    ),
    (
        GateIoSpotPlugin,
        {
            "method": "subscribe",
            "params": ["spot.candlesticks", {"currency_pair": "BTC_USDT", "interval": "1m"}],
        },
        {
            "method": "unsubscribe",
            "params": ["spot.candlesticks", {"currency_pair": "BTC_USDT", "interval": "1m"}],
        },
    ),
    (
        HyperliquidPerpetualPlugin,
        {"method": "subscribe", "channel": "candles", "coin": "BTC", "interval": "1"},
        {"method": "unsubscribe", "channel": "candles", "coin": "BTC", "interval": "1"},
    ),
    (
        KucoinSpotPlugin,
        {"type": "subscribe", "topic": "/market/candles:BTC-USDT_1min"},
        {"type": "unsubscribe", "topic": "/market/candles:BTC-USDT_1min"},
    ),
    (
        AscendExSpotPlugin,
        {"op": "sub", "ch": "bar:1:BTC/USDT"},
        {"op": "unsub", "ch": "bar:1:BTC/USDT"},
    ),
    (
        CoinbaseAdvancedTradeSpotPlugin,
        {"type": "subscribe", "product_ids": ["BTC-USD"], "channel": "candles", "granularity": 60},
        {
            "type": "unsubscribe",
            "product_ids": ["BTC-USD"],
            "channel": "candles",
            "granularity": 60,
        },
    ),
    (
        KrakenSpotPlugin,
        {"name": "subscribe", "pair": ["XBT/USD"], "subscription": {"name": "ohlc", "interval": 1}},
        {
            "name": "unsubscribe",
            "pair": ["XBT/USD"],
            "subscription": {"name": "ohlc", "interval": 1},
        },
    ),
]


@pytest.mark.parametrize(
    ("plugin_cls", "sub_msg", "unsub_msg"),
    CASES,
    ids=[case[0].__name__ for case in CASES],
)
def test_unsubscribe_parses_like_subscribe(plugin_cls, sub_msg, unsub_msg):
    plugin = plugin_cls()
    expected = plugin.parse_ws_subscription(sub_msg)
    assert expected, "subscribe message must parse to at least one subscription"
    assert plugin.parse_ws_subscription(unsub_msg) == expected
