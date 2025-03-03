"""
Example of using the mock Binance Spot exchange server.
"""

import asyncio
import logging
import json

from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server
from candles_feed.testing_resources.candle_data_factory import CandleDataFactory
from candles_feed.core.candle_data import CandleData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_candle(candle: CandleData):
    """Print candle information in a readable format."""
    print(f"Candle at {candle.timestamp} ({candle.timestamp_ms} ms):")
    print(f"  OHLC: {candle.open:.2f}, {candle.high:.2f}, {candle.low:.2f}, {candle.close:.2f}")
    print(f"  Volume: {candle.volume:.2f}")
    print(f"  Trades: {candle.n_trades}")
    

async def main():
    """Run a simple example of the mock Binance Spot exchange server."""
    # Create a mock Binance Spot server
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host='127.0.0.1',
        port=8080,
        trading_pairs=[
            ("BTCUSDT", "1m", 50000.0),
            ("ETHUSDT", "1m", 3000.0),
            ("SOLUSDT", "1m", 100.0)
        ]
    )
    
    if server is None:
        logger.error("Failed to create mock server")
        return
    
    # Start the server
    url = await server.start()
    logger.info(f"Mock Binance Spot server started at {url}")
    
    # Print trading pairs
    for pair_key, price in server.trading_pairs.items():
        logger.info(f"Trading pair: {pair_key}, Price: {price}")
    
    # Generate some random candle data for demonstration
    logger.info("Generating random candle data:")
    timestamp = int(asyncio.get_event_loop().time())
    
    # Create a sequence of candles
    candles = []
    prev_candle = None
    
    for i in range(5):
        candle_timestamp = timestamp + (i * 60)  # 1-minute intervals
        
        if prev_candle is None:
            # First candle
            candle = CandleDataFactory.create_random(candle_timestamp, base_price=50000.0)
        else:
            # Subsequent candles based on previous
            candle = CandleDataFactory.create_random(candle_timestamp, previous_candle=prev_candle)
        
        candles.append(candle)
        prev_candle = candle
        
        # Print candle info
        print_candle(candle)
    
    # Format candle data as a Binance REST response
    rest_response = [
        [
            c.timestamp_ms,               # Open time
            str(c.open),                  # Open
            str(c.high),                  # High
            str(c.low),                   # Low
            str(c.close),                 # Close
            str(c.volume),                # Volume
            c.timestamp_ms + (60 * 1000), # Close time (1-minute interval)
            str(c.quote_asset_volume),    # Quote asset volume
            c.n_trades,                   # Number of trades
            str(c.taker_buy_base_volume), # Taker buy base asset volume
            str(c.taker_buy_quote_volume),# Taker buy quote asset volume
            "0"                           # Unused field
        ]
        for c in candles
    ]
    
    # Format candle data as a Binance WebSocket message
    ws_message = {
        "e": "kline",                        # Event type
        "E": int(asyncio.get_event_loop().time() * 1000),  # Event time
        "s": "BTCUSDT",                      # Symbol
        "k": {
            "t": candles[-1].timestamp_ms,   # Kline start time
            "T": candles[-1].timestamp_ms + (60 * 1000),  # Kline close time
            "s": "BTCUSDT",                  # Symbol
            "i": "1m",                       # Interval
            "f": 100000000,                  # First trade ID
            "L": 100000100,                  # Last trade ID
            "o": str(candles[-1].open),      # Open price
            "c": str(candles[-1].close),     # Close price
            "h": str(candles[-1].high),      # High price
            "l": str(candles[-1].low),       # Low price
            "v": str(candles[-1].volume),    # Base asset volume
            "n": candles[-1].n_trades,       # Number of trades
            "x": True,                       # Is this kline closed?
            "q": str(candles[-1].quote_asset_volume),  # Quote asset volume
            "V": str(candles[-1].taker_buy_base_volume),  # Taker buy base asset volume
            "Q": str(candles[-1].taker_buy_quote_volume)  # Taker buy quote asset volume
        }
    }
    
    # Print the formatted data
    logger.info("Example REST response:\n" + json.dumps(rest_response, indent=2))
    logger.info("Example WebSocket message:\n" + json.dumps(ws_message, indent=2))
    
    # Stop the server
    await server.stop()
    logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
