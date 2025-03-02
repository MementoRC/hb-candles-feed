"""
Unit tests for the ExchangePlugin abstract base class in testing_resources.
"""

import unittest
from unittest.mock import MagicMock
from typing import Dict, List, Tuple, Any

from aiohttp import web

from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
from candles_feed.testing_resources.mocks.core.candle_data import MockCandleData


class TestExchangePlugin(unittest.TestCase):
    """Tests for the ExchangePlugin abstract base class."""
    
    class ConcreteExchangePlugin(ExchangePlugin):
        """A concrete implementation of ExchangePlugin for testing."""
        
        @property
        def rest_routes(self) -> Dict[str, Tuple[str, str]]:
            return {
                '/api/test': ('GET', 'handle_test'),
                '/api/candles': ('GET', 'handle_klines')
            }
        
        @property
        def ws_routes(self) -> Dict[str, str]:
            return {
                '/ws': 'handle_websocket'
            }
        
        def format_rest_candles(self, candles: List[MockCandleData], 
                             trading_pair: str, interval: str) -> Any:
            return [
                {
                    'timestamp': c.timestamp,
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume
                }
                for c in candles
            ]
        
        def format_ws_candle_message(self, candle: MockCandleData, 
                                  trading_pair: str, interval: str, 
                                  is_final: bool = False) -> Any:
            return {
                'type': 'candle',
                'data': {
                    'timestamp': candle.timestamp,
                    'trading_pair': trading_pair,
                    'interval': interval,
                    'open': candle.open,
                    'high': candle.high,
                    'low': candle.low,
                    'close': candle.close,
                    'volume': candle.volume,
                    'final': is_final
                }
            }
        
        def parse_ws_subscription(self, message: Dict) -> List[Tuple[str, str]]:
            if message.get('type') == 'subscribe':
                channel = message.get('channel')
                if channel == 'candles':
                    trading_pair = message.get('trading_pair')
                    interval = message.get('interval')
                    return [(trading_pair, interval)]
            return []
        
        def create_ws_subscription_success(self, message: Dict, 
                                        subscriptions: List[Tuple[str, str]]) -> Dict:
            return {
                'type': 'subscribed',
                'channel': message.get('channel'),
                'subscriptions': [
                    {
                        'trading_pair': tp,
                        'interval': interval
                    }
                    for tp, interval in subscriptions
                ]
            }
        
        def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
            return f"{trading_pair}_{interval}"
        
        def parse_rest_candles_params(self, request: web.Request) -> Dict[str, Any]:
            params = request.query
            return {
                'symbol': params.get('symbol'),
                'interval': params.get('interval'),
                'start_time': params.get('start'),
                'end_time': params.get('end'),
                'limit': params.get('limit', '100')
            }
    
    def setUp(self):
        """Set up test fixtures."""
        self.exchange_type = ExchangeType.BINANCE_SPOT
        self.plugin = self.ConcreteExchangePlugin(self.exchange_type)
    
    def test_init(self):
        """Test initialization of the plugin."""
        self.assertEqual(self.plugin.exchange_type, self.exchange_type)
    
    def test_rest_routes(self):
        """Test the rest_routes property."""
        routes = self.plugin.rest_routes
        self.assertIsInstance(routes, dict)
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes['/api/test'], ('GET', 'handle_test'))
        self.assertEqual(routes['/api/candles'], ('GET', 'handle_klines'))
    
    def test_ws_routes(self):
        """Test the ws_routes property."""
        routes = self.plugin.ws_routes
        self.assertIsInstance(routes, dict)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes['/ws'], 'handle_websocket')
    
    def test_format_rest_candles(self):
        """Test formatting REST candles response."""
        candles = [
            MockCandleData(
                timestamp=1613677200,
                open=50000.0,
                high=50500.0,
                low=49500.0,
                close=50200.0,
                volume=10.0,
                quote_asset_volume=500000.0,
                n_trades=100,
                taker_buy_base_volume=5.0,
                taker_buy_quote_volume=250000.0
            )
        ]
        
        result = self.plugin.format_rest_candles(candles, 'BTCUSDT', '1m')
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['timestamp'], candles[0].timestamp)
        self.assertEqual(result[0]['open'], candles[0].open)
        self.assertEqual(result[0]['high'], candles[0].high)
        self.assertEqual(result[0]['low'], candles[0].low)
        self.assertEqual(result[0]['close'], candles[0].close)
        self.assertEqual(result[0]['volume'], candles[0].volume)
    
    def test_format_ws_candle_message(self):
        """Test formatting WebSocket candle message."""
        candle = MockCandleData(
            timestamp=1613677200,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=10.0,
            quote_asset_volume=500000.0,
            n_trades=100,
            taker_buy_base_volume=5.0,
            taker_buy_quote_volume=250000.0
        )
        
        result = self.plugin.format_ws_candle_message(
            candle, 'BTCUSDT', '1m', is_final=True
        )
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['type'], 'candle')
        self.assertEqual(result['data']['timestamp'], candle.timestamp)
        self.assertEqual(result['data']['trading_pair'], 'BTCUSDT')
        self.assertEqual(result['data']['interval'], '1m')
        self.assertEqual(result['data']['open'], candle.open)
        self.assertEqual(result['data']['high'], candle.high)
        self.assertEqual(result['data']['low'], candle.low)
        self.assertEqual(result['data']['close'], candle.close)
        self.assertEqual(result['data']['volume'], candle.volume)
        self.assertEqual(result['data']['final'], True)
    
    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        message = {
            'type': 'subscribe',
            'channel': 'candles',
            'trading_pair': 'BTCUSDT',
            'interval': '1m'
        }
        
        result = self.plugin.parse_ws_subscription(message)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ('BTCUSDT', '1m'))
    
    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        message = {
            'type': 'subscribe',
            'channel': 'candles',
            'trading_pair': 'BTCUSDT',
            'interval': '1m'
        }
        subscriptions = [('BTCUSDT', '1m'), ('ETHUSDT', '5m')]
        
        result = self.plugin.create_ws_subscription_success(message, subscriptions)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['type'], 'subscribed')
        self.assertEqual(result['channel'], 'candles')
        self.assertEqual(len(result['subscriptions']), 2)
        self.assertEqual(result['subscriptions'][0]['trading_pair'], 'BTCUSDT')
        self.assertEqual(result['subscriptions'][0]['interval'], '1m')
        self.assertEqual(result['subscriptions'][1]['trading_pair'], 'ETHUSDT')
        self.assertEqual(result['subscriptions'][1]['interval'], '5m')
    
    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        result = self.plugin.create_ws_subscription_key('BTCUSDT', '1m')
        self.assertEqual(result, 'BTCUSDT_1m')
    
    def test_parse_rest_candles_params(self):
        """Test parsing REST candles parameters."""
        # Create a mock request
        mock_request = MagicMock()
        mock_request.query = {
            'symbol': 'BTCUSDT',
            'interval': '1m',
            'start': '1613677200000',
            'end': '1613680800000',
            'limit': '500'
        }
        
        result = self.plugin.parse_rest_candles_params(mock_request)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['symbol'], 'BTCUSDT')
        self.assertEqual(result['interval'], '1m')
        self.assertEqual(result['start_time'], '1613677200000')
        self.assertEqual(result['end_time'], '1613680800000')
        self.assertEqual(result['limit'], '500')
    
    def test_normalize_trading_pair(self):
        """Test normalizing trading pair."""
        result = self.plugin.normalize_trading_pair('btcusdt')
        self.assertEqual(result, 'BTCUSDT')


if __name__ == '__main__':
    unittest.main()