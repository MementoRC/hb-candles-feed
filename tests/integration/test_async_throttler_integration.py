"""
Integration tests for AsyncThrottler and WebAssistantsFactory components.

This module provides comprehensive testing of the integration between
candles-feed and Hummingbot's rate limiting and network components.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.core.hummingbot_network_client_adapter import (
    HummingbotNetworkClient,
    HummingbotThrottlerAdapter,
    HummingbotWSAssistantAdapter,
    NetworkClientFactory,
)
from candles_feed.mocking_resources.hummingbot.mock_components import (
    MockAsyncThrottler,
    MockRESTAssistant,
    MockWebAssistantsFactory,
    MockWSAssistant,
    create_mock_hummingbot_components,
)


@pytest.mark.integration
class TestAsyncThrottlerIntegration:
    """Test AsyncThrottler integration and rate limiting behavior."""

    @pytest.fixture
    def rate_limited_throttler(self):
        """Create a throttler with specific rate limits for testing."""
        rate_limits = [
            {"limit_id": "api_calls", "limit": 5, "time_interval": 1.0},  # 5 calls per second
            {
                "limit_id": "heavy_operations",
                "limit": 2,
                "time_interval": 2.0,
            },  # 2 calls per 2 seconds
        ]
        return MockAsyncThrottler(rate_limits)

    @pytest.mark.asyncio
    async def test_throttler_adapter_basic_functionality(self, rate_limited_throttler):
        """Test basic functionality of HummingbotThrottlerAdapter."""
        adapter = HummingbotThrottlerAdapter(rate_limited_throttler)

        # Test that execute_task works as a context manager
        start_time = time.time()
        async with await adapter.execute_task("api_calls"):
            pass
        execution_time = time.time() - start_time

        # Should execute quickly for first call
        assert execution_time < 0.1, "First call should not be rate limited"

        # Verify task was logged
        assert len(rate_limited_throttler.task_logs) == 1
        assert rate_limited_throttler.task_logs[0][0] == "api_calls"

    @pytest.mark.asyncio
    async def test_throttler_adapter_rate_limiting(self, rate_limited_throttler):
        """Test rate limiting behavior of throttler adapter."""
        adapter = HummingbotThrottlerAdapter(rate_limited_throttler)

        # Execute multiple tasks rapidly
        start_time = time.time()

        for _ in range(3):
            async with await adapter.execute_task("api_calls"):
                pass

        time.time() - start_time

        # Should have logged all 3 tasks
        assert len(rate_limited_throttler.task_logs) == 3
        assert all(log[0] == "api_calls" for log in rate_limited_throttler.task_logs)

    @pytest.mark.asyncio
    async def test_throttler_different_limit_ids(self, rate_limited_throttler):
        """Test that different limit IDs work independently."""
        adapter = HummingbotThrottlerAdapter(rate_limited_throttler)

        # Execute tasks with different limit IDs
        async with await adapter.execute_task("api_calls"):
            pass
        async with await adapter.execute_task("heavy_operations"):
            pass
        async with await adapter.execute_task("api_calls"):
            pass

        # Should have logged 3 tasks with correct IDs
        assert len(rate_limited_throttler.task_logs) == 3
        task_ids = [log[0] for log in rate_limited_throttler.task_logs]
        assert task_ids == ["api_calls", "heavy_operations", "api_calls"]

    @pytest.mark.asyncio
    async def test_throttler_error_handling(self):
        """Test error handling in throttler adapter."""

        # Create a throttler that raises an exception
        class FailingThrottler:
            async def execute_task(self, limit_id: str):
                class FailingContext:
                    async def __aenter__(self):
                        raise RuntimeError("Throttler failure")

                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        return None

                return FailingContext()

        adapter = HummingbotThrottlerAdapter(FailingThrottler())

        # Should propagate the exception
        with pytest.raises(RuntimeError, match="Throttler failure"):
            async with await adapter.execute_task("test_limit"):
                pass


@pytest.mark.integration
class TestWebAssistantsFactoryIntegration:
    """Test WebAssistantsFactory integration and network operations."""

    @pytest.fixture
    def configured_factory(self):
        """Create a WebAssistantsFactory with test responses."""
        rest_responses = {
            "https://api.binance.com/api/v3/klines": [
                [
                    1625097600000,
                    "35000.1",
                    "35100.5",
                    "34900.2",
                    "35050.3",
                    "10.5",
                    1625097899999,
                    "367000.5",
                    100,
                    "5.2",
                    "182000.1",
                    "0",
                ]
            ],
            "https://api.coinbase.com/v2/exchange-rates": {
                "data": {"currency": "BTC", "rates": {"USD": "35000"}}
            },
        }

        ws_messages = [
            json.dumps(
                {
                    "e": "kline",
                    "E": 1625098200000,
                    "s": "BTCUSDT",
                    "k": {
                        "t": 1625098200000,
                        "o": "35150.2",
                        "c": "35200.1",
                        "h": "35250.0",
                        "l": "35100.0",
                    },
                }
            )
        ]

        return MockWebAssistantsFactory(rest_responses=rest_responses, ws_messages=ws_messages)

    @pytest.mark.asyncio
    async def test_rest_assistant_creation(self, configured_factory):
        """Test REST assistant creation from factory."""
        rest_assistant = await configured_factory.get_rest_assistant()

        assert isinstance(rest_assistant, MockRESTAssistant)
        assert rest_assistant.connection is configured_factory.rest_connection

    @pytest.mark.asyncio
    async def test_ws_assistant_creation(self, configured_factory):
        """Test WebSocket assistant creation from factory."""
        ws_assistant = await configured_factory.get_ws_assistant()

        assert isinstance(ws_assistant, MockWSAssistant)
        assert ws_assistant.connection is configured_factory.ws_connection

    @pytest.mark.asyncio
    async def test_rest_assistant_api_calls(self, configured_factory):
        """Test REST API calls through assistant."""
        rest_assistant = await configured_factory.get_rest_assistant()

        # Make a REST call
        response = await rest_assistant.call(
            url="https://api.binance.com/api/v3/klines",
            method="GET",
            params={"symbol": "BTCUSDT", "interval": "1m"},
        )

        # Verify response
        response_data = await response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 1
        assert response_data[0][1] == "35000.1"  # Open price

        # Verify request was logged
        requests = configured_factory.rest_connection.requests
        assert len(requests) == 1
        assert requests[0]["url"] == "https://api.binance.com/api/v3/klines"
        assert requests[0]["method"] == "GET"
        assert requests[0]["params"]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_ws_assistant_connection_and_messaging(self, configured_factory):
        """Test WebSocket connection and message handling."""
        ws_assistant = await configured_factory.get_ws_assistant()

        # Connect to WebSocket
        await ws_assistant.connect("wss://stream.binance.com/ws/btcusdt@kline_1m")
        assert ws_assistant.connection.connected
        assert ws_assistant.connection.url == "wss://stream.binance.com/ws/btcusdt@kline_1m"

        # Send a message
        subscription_msg = {"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 1}
        await ws_assistant.send(subscription_msg)

        # Verify message was sent
        sent_messages = ws_assistant.connection.sent_messages
        assert len(sent_messages) == 1
        assert sent_messages[0]["method"] == "SUBSCRIBE"

        # Receive messages
        messages = []
        async for message in ws_assistant.iter_messages():
            messages.append(message.data)
            break  # Only get first message for test

        assert len(messages) == 1
        message_data = json.loads(messages[0])
        assert message_data["e"] == "kline"
        assert message_data["s"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_factory_async_context_manager(self, configured_factory):
        """Test factory as async context manager."""
        async with configured_factory as factory:
            # Should be able to use factory normally
            rest_assistant = await factory.get_rest_assistant()
            assert rest_assistant is not None

            ws_assistant = await factory.get_ws_assistant()
            await ws_assistant.connect("wss://test.com/ws")
            assert ws_assistant.connection.connected

        # After context exit, connections should be closed
        assert not configured_factory.ws_connection.connected


@pytest.mark.integration
class TestHummingbotNetworkClientIntegration:
    """Test HummingbotNetworkClient integration with all components."""

    @pytest.fixture
    def integrated_components(self):
        """Create integrated Hummingbot components for testing."""
        return create_mock_hummingbot_components(
            rest_responses={
                "https://api.test.com/candles": [
                    ["1625097600000", "35000", "35100", "34900", "35050", "10.5"]
                ],
                "https://api.test.com/ticker": {"symbol": "BTCUSDT", "price": "35000.50"},
            },
            ws_messages=[
                json.dumps({"type": "kline", "data": {"symbol": "BTCUSDT", "price": "35100"}})
            ],
            rate_limits=[{"limit_id": "api_requests", "limit": 10, "time_interval": 1.0}],
        )

    @pytest.mark.asyncio
    async def test_network_client_creation_with_components(self, integrated_components):
        """Test creating HummingbotNetworkClient with components."""
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = HummingbotNetworkClient(
                throttler=integrated_components["throttler"],
                web_assistants_factory=integrated_components["web_assistants_factory"],
            )

            assert client._throttler is integrated_components["throttler"]
            assert client._web_assistants_factory is integrated_components["web_assistants_factory"]
            assert isinstance(client._throttler_adapter, HummingbotThrottlerAdapter)

    @pytest.mark.asyncio
    async def test_network_client_rest_operations(self, integrated_components):
        """Test REST operations through network client."""
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = HummingbotNetworkClient(
                throttler=integrated_components["throttler"],
                web_assistants_factory=integrated_components["web_assistants_factory"],
            )

            # Test REST call
            response = await client.get_rest_data(
                url="https://api.test.com/candles", params={"symbol": "BTCUSDT", "interval": "1m"}
            )

            # Verify response
            assert isinstance(response, list)
            assert len(response) == 1
            assert response[0][1] == "35000"  # Open price

            # Verify throttler was used
            throttler_logs = integrated_components["throttler"].task_logs
            assert len(throttler_logs) >= 1

    @pytest.mark.asyncio
    async def test_network_client_websocket_operations(self, integrated_components):
        """Test WebSocket operations through network client."""
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = HummingbotNetworkClient(
                throttler=integrated_components["throttler"],
                web_assistants_factory=integrated_components["web_assistants_factory"],
            )

            # Establish WebSocket connection
            ws_assistant = await client.establish_ws_connection("wss://api.test.com/ws")

            assert isinstance(ws_assistant, HummingbotWSAssistantAdapter)

            # Send subscription message
            subscription = {"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m"]}
            await client.send_ws_message(ws_assistant, subscription)

            # Verify message was sent
            factory = integrated_components["web_assistants_factory"]
            sent_messages = factory.ws_connection.sent_messages
            assert len(sent_messages) == 1
            assert sent_messages[0]["method"] == "SUBSCRIBE"

    @pytest.mark.asyncio
    async def test_network_client_context_manager(self, integrated_components):
        """Test network client as async context manager."""
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            async with HummingbotNetworkClient(
                throttler=integrated_components["throttler"],
                web_assistants_factory=integrated_components["web_assistants_factory"],
            ) as client:
                # Should have REST assistant initialized
                assert client._rest_assistant is not None

                # Should be able to make requests
                response = await client.get_rest_data("https://api.test.com/ticker")
                assert response["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_network_client_error_handling(self, integrated_components):
        """Test error handling in network client operations."""
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = HummingbotNetworkClient(
                throttler=integrated_components["throttler"],
                web_assistants_factory=integrated_components["web_assistants_factory"],
            )

            # Test with URL that doesn't have a configured response
            with pytest.raises(
                ValueError, match="No mock response configured"
            ):  # Should raise an error for unknown URL
                await client.get_rest_data("https://api.unknown.com/invalid")


@pytest.mark.integration
class TestNetworkClientFactory:
    """Test NetworkClientFactory component selection logic."""

    @pytest.mark.asyncio
    async def test_factory_with_hummingbot_components(self):
        """Test factory creates HummingbotNetworkClient when components provided."""
        components = create_mock_hummingbot_components()

        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = NetworkClientFactory.create_client(hummingbot_components=components)

            assert isinstance(client, HummingbotNetworkClient)
            assert client._throttler is components["throttler"]
            assert client._web_assistants_factory is components["web_assistants_factory"]

    @pytest.mark.asyncio
    async def test_factory_fallback_to_standalone(self):
        """Test factory falls back to standalone client when components unavailable."""
        # Test with no components
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", False
        ):
            client = NetworkClientFactory.create_client()

            # Should fall back to standalone NetworkClient
            from candles_feed.core.network_client import NetworkClient

            assert isinstance(client, NetworkClient)

    @pytest.mark.asyncio
    async def test_factory_partial_components(self):
        """Test factory behavior with partial component set."""
        # Only provide throttler, no web_assistants_factory
        partial_components = {"throttler": MockAsyncThrottler()}

        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = NetworkClientFactory.create_client(hummingbot_components=partial_components)

            # Should fall back to standalone client
            from candles_feed.core.network_client import NetworkClient

            assert isinstance(client, NetworkClient)


@pytest.mark.integration
class TestWSAssistantAdapter:
    """Test HummingbotWSAssistantAdapter functionality."""

    @pytest.fixture
    def mock_ws_assistant(self):
        """Create a mock Hummingbot WSAssistant."""
        ws_mock = MagicMock()
        ws_mock.disconnect = AsyncMock()
        ws_mock.send = AsyncMock()

        # Mock iter_messages to return test data
        async def mock_iter_messages():
            class MockWSResponse:
                def __init__(self, data):
                    self.data = data

            yield MockWSResponse('{"type": "test", "value": 123}')
            yield MockWSResponse('{"type": "ping"}')

        ws_mock.iter_messages = mock_iter_messages
        return ws_mock

    @pytest.mark.asyncio
    async def test_ws_adapter_basic_operations(self, mock_ws_assistant):
        """Test basic WebSocket adapter operations."""
        adapter = HummingbotWSAssistantAdapter(mock_ws_assistant)

        # Test sending messages
        await adapter.send({"method": "subscribe", "channel": "ticker"})
        mock_ws_assistant.send.assert_called_once_with(
            '{"method": "subscribe", "channel": "ticker"}'
        )

        # Test sending string messages
        await adapter.send("ping")
        mock_ws_assistant.send.assert_called_with("ping")

    @pytest.mark.asyncio
    async def test_ws_adapter_message_iteration(self, mock_ws_assistant):
        """Test WebSocket message iteration and parsing."""
        adapter = HummingbotWSAssistantAdapter(mock_ws_assistant)

        messages = []
        async for message in adapter.iter_messages():
            messages.append(message)

        assert len(messages) == 2
        assert messages[0]["type"] == "test"
        assert messages[0]["value"] == 123
        assert messages[1]["type"] == "ping"

    @pytest.mark.asyncio
    async def test_ws_adapter_error_handling(self):
        """Test WebSocket adapter error handling."""
        # Create a mock that raises an exception
        failing_ws = MagicMock()

        class FailingAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise ConnectionError("WebSocket connection lost")

        failing_ws.iter_messages.return_value = FailingAsyncIterator()

        adapter = HummingbotWSAssistantAdapter(failing_ws)

        # Should propagate the exception
        with pytest.raises(ConnectionError, match="WebSocket connection lost"):
            async for _ in adapter.iter_messages():
                pass

    @pytest.mark.asyncio
    async def test_ws_adapter_json_parse_error_handling(self, mock_ws_assistant):
        """Test handling of invalid JSON messages."""

        # Override the mock to return invalid JSON
        async def mock_iter_with_invalid_json():
            class MockWSResponse:
                def __init__(self, data):
                    self.data = data

            yield MockWSResponse('{"valid": "json"}')
            yield MockWSResponse("invalid json{")  # Invalid JSON
            yield MockWSResponse('{"another": "valid"}')

        mock_ws_assistant.iter_messages = mock_iter_with_invalid_json

        adapter = HummingbotWSAssistantAdapter(mock_ws_assistant)

        messages = []
        async for message in adapter.iter_messages():
            messages.append(message)

        # Should get valid messages and skip invalid JSON
        assert len(messages) == 2
        assert messages[0]["valid"] == "json"
        assert messages[1]["another"] == "valid"
