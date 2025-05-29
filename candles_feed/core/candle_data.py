"""
Structured candle data representation for the Candle Feed V2 framework.
"""

from dataclasses import InitVar, dataclass, field
from datetime import datetime, timezone
from typing import ClassVar


@dataclass
class CandleData:
    """Standardized candle data representation.

    This class provides a structured and type-safe representation of candle data
    with automatic timestamp normalization.

    :ivar timestamp: The candle timestamp in seconds
    :ivar open: Opening price
    :ivar high: Highest price during period
    :ivar low: Lowest price during period
    :ivar close: Closing price
    :ivar volume: Trading volume
    :ivar quote_asset_volume: Quote asset volume (optional)
    :ivar n_trades: Number of trades (optional)
    :ivar taker_buy_base_volume: Base asset volume from taker buys (optional)
    :ivar taker_buy_quote_volume: Quote asset volume from taker buys (optional)
    """

    timestamp_raw: InitVar[int | float | str | datetime]

    timestamp: int = field(init=False)
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_asset_volume: float = 0.0
    n_trades: int = 0
    taker_buy_base_volume: float = 0.0
    taker_buy_quote_volume: float = 0.0

    @property
    def timestamp_ms(self) -> int:
        """Convert timestamp to milliseconds."""
        return self.timestamp * 1000

    _timestamp_keys: ClassVar[tuple[str, ...]] = ("timestamp", "time", "t")
    _price_keys: ClassVar[dict[str, tuple[str, ...]]] = {
        "open": ("open", "o"),
        "high": ("high", "h"),
        "low": ("low", "l"),
        "close": ("close", "c"),
        "volume": ("volume", "v"),
    }

    def __post_init__(self, timestamp_raw: int | float | str | datetime) -> None:
        """Convert timestamp to integer seconds after initialization.

        :param timestamp_raw: Raw timestamp input in various formats
        """
        self.timestamp = self._normalize_timestamp(timestamp_raw)

    @staticmethod
    def _normalize_timestamp(ts: int | float | str | datetime) -> int:
        """Convert various timestamp formats to integer seconds.

        :param ts: Timestamp in various formats
        :return: Timestamp as integer seconds
        :raises ValueError: If timestamp cannot be converted
        """
        if isinstance(ts, int):
            # Handle milliseconds/microseconds timestamps
            if ts > 10000000000:  # Likely milliseconds or microseconds
                return ts // 1000000 if ts > 10000000000000 else ts // 1000
            return ts
        elif isinstance(ts, float):
            # Handle floating point timestamps (potentially with fractional seconds)
            if ts > 10000000000:  # Likely milliseconds or microseconds
                return int(ts) // 1000000 if ts > 10000000000000 else int(ts) // 1000
            return int(ts)
        elif isinstance(ts, str):
            try:
                # Try parsing as Unix timestamp first
                return CandleData._normalize_timestamp(float(ts))
            except ValueError:
                try:
                    # Try parsing as ISO format
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    return CandleData.to_utc_seconds(dt)
                except ValueError as e:
                    raise ValueError(f"Could not parse timestamp string: {ts}") from e
        elif isinstance(ts, datetime):
            return CandleData.to_utc_seconds(ts)
        else:
            raise ValueError(f"Unsupported timestamp type: {type(ts)}")

    @staticmethod
    def to_utc_seconds(dt: datetime) -> int:
        """Convert datetime to UTC timestamp in seconds.

        :param dt: Datetime to convert
        :return: UTC timestamp in seconds
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp())

    def to_array(self) -> list[float]:
        """Convert to array format for backward compatibility.

        :return: List of candle values
        """
        return [
            float(self.timestamp),
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.quote_asset_volume,
            self.n_trades,
            self.taker_buy_base_volume,
            self.taker_buy_quote_volume,
        ]

    @classmethod
    def from_array(cls, data: list[float]) -> "CandleData":
        """Create from array format for backward compatibility.

        :param data: Array of candle values
        :return: CandleData instance
        """
        return cls(
            timestamp_raw=data[0],
            open=data[1],
            high=data[2],
            low=data[3],
            close=data[4],
            volume=data[5],
            quote_asset_volume=data[6],
            n_trades=int(data[7]),
            taker_buy_base_volume=data[8],
            taker_buy_quote_volume=data[9],
        )

    @classmethod
    def from_dict(cls, data: dict) -> "CandleData":
        """Create CandleData from a dictionary.

        :param data: Dictionary containing candle data
        :return: CandleData instance
        :raises ValueError: If required fields are missing or invalid
        """
        timestamp_raw = next((data[key] for key in cls._timestamp_keys if key in data), None)
        if timestamp_raw is None:
            raise ValueError(f"No timestamp found in keys: {cls._timestamp_keys}")

        # Find price values
        values: dict[str, float | int] = {}
        for f, keys in cls._price_keys.items():
            value = next((float(data[key]) for key in keys if key in data), None)
            if value is None:
                raise ValueError(f"No {f} value found in keys: {keys}")
            values[f] = value

        # Return with explicit parameters instead of unpacking dictionaries
        return cls(
            timestamp_raw=timestamp_raw,
            open=values["open"],
            high=values["high"],
            low=values["low"],
            close=values["close"],
            volume=values["volume"],
            quote_asset_volume=float(data.get("quote_asset_volume", 0)),
            n_trades=int(data.get("n_trades", 0)),
            taker_buy_base_volume=float(data.get("taker_buy_base_volume", 0)),
            taker_buy_quote_volume=float(data.get("taker_buy_quote_volume", 0)),
        )
