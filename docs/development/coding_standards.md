# Coding Standards

This guide outlines the coding standards and best practices for the Candles Feed project. Following these standards ensures consistency, readability, and maintainability across the codebase.

## Python Version

The project uses Python 3.12+ features and follows modern Python conventions:

```python
# Do this - Python 3.12+ style
data: dict[str, int] = {"key": 42}
values: list[float] = [1.0, 2.0, 3.0]
result: int | None = None
```

## Type Hints

### Collection Types

Use the built-in collection types for type hints, not those from the `typing` module:

```python
# Do this (Python 3.9+)
from collections import deque

def process_items(items: list[int], cache: dict[str, float], queue: deque[str]) -> None:
    pass

# Don't do this (Python 3.8 or earlier style)
from typing import Dict, List, Deque

def process_items(items: List[int], cache: Dict[str, float], queue: Deque[str]) -> None:
    pass
```

### Union Types

Use the union operator (`|`) for union types, not `Union` from the `typing` module:

```python
# Do this (Python 3.10+)
def get_value(key: str) -> int | float | None:
    pass

# Don't do this
from typing import Union
def get_value(key: str) -> Union[int, float, None]:
    pass
```

### Optional Types

Use the union with `None` for optional types, not `Optional` from the `typing` module:

```python
# Do this (Python 3.10+)
def process(value: str | None = None) -> None:
    pass

# Don't do this
from typing import Optional
def process(value: Optional[str] = None) -> None:
    pass
```

## Docstrings

All classes, methods, and functions should have docstrings in reStructuredText format:

```python
def get_trading_pair_format(self, trading_pair: str) -> str:
    """
    Format a trading pair according to exchange requirements.

    :param trading_pair: The trading pair in standard format (e.g., "BTC-USDT")
    :return: The exchange-specific trading pair format (e.g., "BTCUSDT")
    :raises ValueError: If the trading pair is invalid
    :note: Different exchanges may have different formats for trading pairs
    """
    # Implementation...
```

### Docstring Structure

1. **Summary Line**: A brief one-line description
2. **Blank Line**: Required after the summary
3. **Detailed Description**: If needed
4. **Parameter Section**: List all parameters with descriptions
5. **Return Section**: Describe the return value
6. **Raise Section**: List all exceptions that may be raised
7. **Note Section**: Additional notes if necessary

## Method Signatures

For methods with multiple parameters, use the following alignment:

```python
def fetch_historical_data(
    self,
    trading_pair: str,
    interval: str,
    start_time: int | None = None,
    end_time: int | None = None,
    limit: int = 100
) -> list[CandleData]:
    """Method docstring..."""
    # Implementation...
```

### Return Types

Always specify return types, including `None` for methods that don't return a value:

```python
def start_feed(self) -> None:
    """Start the data feed."""
    # Implementation...

def get_candles(self) -> list[CandleData]:
    """Get current candles data."""
    return list(self._candles)
```

## Code Structure

### Class Attributes

Use `ClassVar` for class-level attributes:

```python
from typing import ClassVar

class ExchangeAdapter:
    # Class-level constants
    SUPPORTED_INTERVALS: ClassVar[dict[str, int]] = {
        "1m": 60,
        "5m": 300,
        "1h": 3600
    }

    # Instance attributes
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._is_connected = False
```

### Error Handling

Use proper exception chaining and helpful error messages:

```python
try:
    response = await self._network_client.fetch(url)
    return self._parse_response(response)
except NetworkError as e:
    raise ExchangeConnectionError(f"Failed to connect to {self.exchange_name}") from e
except InvalidResponseError as e:
    raise DataParsingError(f"Invalid response format: {e}") from e
```

## Variable Naming

Follow these naming conventions:

1. **Class Names**: `CamelCase` (e.g., `CandleData`, `BinanceAdapter`)
2. **Function/Method Names**: `snake_case` (e.g., `get_candles`, `format_trading_pair`)
3. **Variable Names**: `snake_case` (e.g., `candle_data`, `trading_pair`)
4. **Constants**: `UPPER_CASE` (e.g., `DEFAULT_TIMEOUT`, `API_VERSION`)
5. **Private Members**: Prefix with underscore (e.g., `_candles`, `_fetch_data`)

## Additional Best Practices

1. **Line Length**: Maximum 100 characters (soft limit)
2. **Import Order**: Standard library, third-party, local modules
3. **Whitespace**: Follow PEP 8 conventions
4. **Comments**: Use them sparingly to explain "why", not "what"
5. **String Formatting**: Use f-strings instead of older methods when possible
6. **Type Guards**: Use explicit type checking where necessary

## Lint and Type Checking

All code must pass the following checks before being submitted:

```bash
# Run the linter
python -m mypy candles_feed

# Run type checking
python -m mypy candles_feed
```

## Recommended IDE Setup

We recommend using:

1. Visual Studio Code with:
   - Python extension
   - Pylance (for type checking)
   - Black formatter
   - Ruff (for linting)

2. PyCharm with:
   - Built-in type checking enabled
   - Black plugin
   - Mypy plugin

## Code Samples

### Correct Class Definition

```python
from typing import ClassVar, Protocol

class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...

class CandleDataProcessor:
    """
    Process and validate candle data.
    """

    MAX_CANDLES: ClassVar[int] = 1000

    def __init__(self, logger: Logger | None = None):
        """
        Initialize the processor.

        :param logger: Logger instance for logging events
        """
        self._logger = logger
        self._candles: dict[str, list[CandleData]] = {}

    def process_candle(self, candle: CandleData, symbol: str) -> bool:
        """
        Process a new candle.

        :param candle: The candle data to process
        :param symbol: The trading pair symbol
        :return: True if the candle was processed, False otherwise
        """
        try:
            self._validate_candle(candle)
            self._store_candle(candle, symbol)
            return True
        except ValueError as e:
            if self._logger:
                self._logger.warning(f"Invalid candle data: {e}")
            return False
```

### Correct Error Handling

```python
async def fetch_data(self, url: str, params: dict[str, str]) -> dict[str, any]:
    """
    Fetch data from an API endpoint.

    :param url: The URL to fetch from
    :param params: Query parameters
    :return: The parsed JSON response
    :raises ConnectionError: If the connection fails
    :raises TimeoutError: If the request times out
    :raises APIError: If the API returns an error
    """
    try:
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except aiohttp.ClientConnectionError as e:
        raise ConnectionError(f"Failed to connect to {url}") from e
    except aiohttp.ClientResponseError as e:
        raise APIError(f"API error: {e.status} - {e.message}") from e
    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Request to {url} timed out") from e
```
