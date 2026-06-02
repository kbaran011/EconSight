import httpx
import pytest
import respx
import tenacity.asyncio

from econsight.clients.base import BaseApiClient


@pytest.fixture
def client() -> BaseApiClient:
    return BaseApiClient(base_url="https://test.example.com/")


async def test_get_returns_json_on_200(client: BaseApiClient) -> None:
    with respx.mock:
        respx.get("https://test.example.com/data").mock(
            return_value=httpx.Response(200, json={"key": "value"})
        )
        result = await client._get("data")
    assert result == {"key": "value"}


async def test_get_retries_on_server_error(
    client: BaseApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def instant_sleep(_: float) -> None:
        pass
    monkeypatch.setattr(tenacity.asyncio, "_portable_async_sleep", instant_sleep)

    with respx.mock:
        route = respx.get("https://test.example.com/data")
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(200, json={"ok": True}),
        ]
        result = await client._get("data")

    assert result == {"ok": True}
    assert route.call_count == 2


async def test_get_raises_after_max_retries(
    client: BaseApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def instant_sleep(_: float) -> None:
        pass
    monkeypatch.setattr(tenacity.asyncio, "_portable_async_sleep", instant_sleep)

    with respx.mock:
        respx.get("https://test.example.com/data").mock(
            return_value=httpx.Response(503)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client._get("data")


async def test_context_manager_closes_client() -> None:
    async with BaseApiClient(base_url="https://test.example.com/") as c:
        assert not c._client.is_closed
    assert c._client.is_closed
