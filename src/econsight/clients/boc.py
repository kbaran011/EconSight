import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from econsight.clients.base import BaseApiClient
from econsight.config import get_logger, settings

logger = get_logger(__name__)


@dataclass
class BocObservation:
    series_key: str
    reference_date: date      # first day of month
    value: Decimal
    ingested_at: datetime


class BocClient(BaseApiClient):
    SERIES: dict[str, str] = {
        "overnight_rate": "V39079",
    }

    def __init__(self) -> None:
        super().__init__(base_url=settings.boc_base_url)

    async def fetch_series(self, series_key: str) -> list[BocObservation]:
        path = f"observations/{series_key}/json"
        raw: dict[str, Any] = await self._get(path, start_date="2010-01-01")
        return self._parse(raw, series_key)

    def _parse(self, raw: dict[str, Any], series_key: str) -> list[BocObservation]:
        observations_raw = raw.get("observations", [])
        now = datetime.now(tz=UTC)
        # Group by (year, month) — keep last non-empty value (month-end)
        monthly: dict[tuple[int, int], BocObservation] = {}
        for obs in observations_raw:
            value_str = (obs.get(series_key) or {}).get("v", "")
            if not value_str:
                continue
            obs_date = date.fromisoformat(obs["d"])
            key = (obs_date.year, obs_date.month)
            monthly[key] = BocObservation(
                series_key=series_key,
                reference_date=date(obs_date.year, obs_date.month, 1),
                value=Decimal(value_str),
                ingested_at=now,
            )
        return list(monthly.values())

    async def fetch_all(self) -> list[BocObservation]:
        batches = await asyncio.gather(*[
            self.fetch_series(sk) for sk in self.SERIES.values()
        ])
        return [obs for batch in batches for obs in batch]
