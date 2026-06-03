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


@pytest.mark.parametrize("name,series_key,fixture_file", [
    ("overnight_rate", "V39079",    "boc_overnight.json"),
    ("cadusd",         "FXCADUSD",  "boc_cadusd.json"),
    ("bond_10yr",      "V122487",   "boc_bond10yr.json"),
    ("m2pp",           "V41552796", "boc_m2pp.json"),
])
async def test_fetch_series_returns_observations(
    client: BocClient,
    respx_mock: respx.MockRouter,
    name: str,
    series_key: str,
    fixture_file: str,
) -> None:
    fixture = json.loads((FIXTURES / fixture_file).read_text())
    respx_mock.get(url__regex=rf".*{series_key}.*").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    obs = await client.fetch_series(series_key)
    assert len(obs) > 0, f"No observations for {name}"
    assert all(o.series_key == series_key for o in obs)
    assert all(o.reference_date.day == 1 for o in obs)  # always first of month


async def test_fetch_all_returns_all_4_series(
    client: BocClient, respx_mock: respx.MockRouter
) -> None:
    fixture_map = {
        "V39079":    "boc_overnight.json",
        "FXCADUSD":  "boc_cadusd.json",
        "V122487":   "boc_bond10yr.json",
        "V41552796": "boc_m2pp.json",
    }
    for sk, fname in fixture_map.items():
        fixture = json.loads((FIXTURES / fname).read_text())
        respx_mock.get(url__regex=rf".*{sk}.*").mock(
            return_value=httpx.Response(200, json=fixture)
        )
    obs = await client.fetch_all()
    keys = {o.series_key for o in obs}
    assert keys == set(BocClient.SERIES.values())
