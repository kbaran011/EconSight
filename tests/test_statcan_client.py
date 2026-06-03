import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from econsight.clients.statcan import StatCanClient, StatCanObservation

FIXTURES = Path(__file__).parent / "fixtures"

# Mapping from indicator name to fixture filename
INDICATOR_FIXTURES: dict[str, str] = {
    "cpi":          "statcan_cpi.json",
    "gdp":          "statcan_gdp.json",
    "unemployment": "statcan_unemployment.json",
    "ippi":         "statcan_ippi.json",
    "retail_trade": "statcan_retail.json",
}


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


@pytest.mark.parametrize("name,table_id,fixture_file", [
    ("cpi",          "18-10-0004-01", "statcan_cpi.json"),
    ("gdp",          "36-10-0104-01", "statcan_gdp.json"),
    ("unemployment", "14-10-0287-01", "statcan_unemployment.json"),
    ("ippi",         "18-10-0266-01", "statcan_ippi.json"),
    ("retail_trade", "20-10-0008-01", "statcan_retail.json"),
])
async def test_fetch_indicator_returns_observations(
    client: StatCanClient,
    respx_mock: respx.MockRouter,
    name: str,
    table_id: str,
    fixture_file: str,
) -> None:
    fixture = json.loads((FIXTURES / fixture_file).read_text())
    respx_mock.post(
        url__regex=r".*getDataFromCubePidCoordAndLatestNPeriods.*"
    ).mock(return_value=httpx.Response(200, json=fixture))
    obs = await client.fetch_indicator(table_id)
    assert len(obs) > 0, f"No observations parsed for {name}"
    assert all(o.indicator_key == table_id for o in obs)


async def test_fetch_all_returns_all_5_indicators(
    client: StatCanClient, respx_mock: respx.MockRouter
) -> None:
    # Load all fixtures in INDICATORS order so side_effect round-robin lines up
    # with the order fetch_all() issues requests (which mirrors INDICATORS dict order)
    responses = [
        httpx.Response(200, json=json.loads((FIXTURES / INDICATOR_FIXTURES[name]).read_text()))
        for name in StatCanClient.INDICATORS
    ]
    respx_mock.post(
        url__regex=r".*getDataFromCubePidCoordAndLatestNPeriods.*"
    ).mock(side_effect=responses)
    obs = await client.fetch_all()
    keys = {o.indicator_key for o in obs}
    assert keys == {tid for _, (tid, _, _) in StatCanClient.INDICATORS.items()}
