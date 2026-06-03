import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from econsight.clients.boc import BocClient, BocObservation

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def overnight_fixture() -> dict:
    return json.loads((FIXTURES / "boc_overnight.json").read_text())


@pytest.fixture
def client() -> BocClient:
    return BocClient()


async def test_fetch_overnight_returns_observations(
    client: BocClient, overnight_fixture: dict, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(url__regex=r".*V39079.*").mock(
        return_value=httpx.Response(200, json=overnight_fixture)
    )
    obs = await client.fetch_series("V39079")
    assert len(obs) > 0
    assert all(isinstance(o, BocObservation) for o in obs)


async def test_daily_aggregates_to_month_end(
    client: BocClient, respx_mock: respx.MockRouter
) -> None:
    payload = {"observations": [
        {"d": "2024-01-03", "V39079": {"v": "5.00"}},
        {"d": "2024-01-17", "V39079": {"v": "5.00"}},
        {"d": "2024-01-31", "V39079": {"v": "5.25"}},  # month-end
    ]}
    respx_mock.get(url__regex=r".*V39079.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    obs = await client.fetch_series("V39079")
    assert len(obs) == 1
    assert obs[0].reference_date == date(2024, 1, 1)
    assert obs[0].value == Decimal("5.25")  # last value wins


async def test_skips_missing_values(
    client: BocClient, respx_mock: respx.MockRouter
) -> None:
    payload = {"observations": [
        {"d": "2024-02-01", "V39079": {"v": ""}},
        {"d": "2024-02-28", "V39079": {"v": "5.00"}},
    ]}
    respx_mock.get(url__regex=r".*V39079.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    obs = await client.fetch_series("V39079")
    assert len(obs) == 1
    assert obs[0].value == Decimal("5.00")
