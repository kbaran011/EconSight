import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from econsight.clients.statcan import StatCanClient, StatCanObservation

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cpi_fixture() -> list:
    return json.loads((FIXTURES / "statcan_cpi.json").read_text())


@pytest.fixture
def client() -> StatCanClient:
    return StatCanClient()


async def test_fetch_cpi_returns_observations(
    client: StatCanClient, cpi_fixture: list, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(
        url__regex=r".*getDataFromCubePidCoordAndLatestNPeriods.*"
    ).mock(return_value=httpx.Response(200, json=cpi_fixture))

    obs = await client.fetch_indicator("18-10-0004-01")

    assert len(obs) > 0
    assert all(isinstance(o, StatCanObservation) for o in obs)


async def test_observation_fields_are_typed(
    client: StatCanClient, cpi_fixture: list, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(url__regex=r".*getDataFromCubePidCoordAndLatestNPeriods.*").mock(
        return_value=httpx.Response(200, json=cpi_fixture)
    )
    obs = await client.fetch_indicator("18-10-0004-01")
    first = obs[0]

    assert isinstance(first.indicator_key, str)
    assert isinstance(first.reference_date, date)
    assert isinstance(first.value, Decimal)
    assert first.status in ("A", "P")


async def test_fetch_skips_null_values(
    client: StatCanClient, respx_mock: respx.MockRouter
) -> None:
    payload = [{"status": "SUCCESS", "object": {
        "responseStatusCode": 0,
        "vectorDataPoint": [
            {"refPer": "2024-01-01", "value": None, "statusCode": 0},
            {"refPer": "2024-02-01", "value": 161.0, "statusCode": 0},
        ],
    }}]
    respx_mock.post(url__regex=r".*getDataFromCubePidCoordAndLatestNPeriods.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    obs = await client.fetch_indicator("18-10-0004-01")
    assert len(obs) == 1
    assert obs[0].reference_date == date(2024, 2, 1)
