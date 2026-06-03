import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from econsight.clients.base import BaseApiClient
from econsight.config import get_logger, settings

logger = get_logger(__name__)


@dataclass
class StatCanObservation:
    indicator_key: str
    reference_date: date
    value: Decimal
    status: str  # "A" (final) or "P" (preliminary)
    ingested_at: datetime


class StatCanClient(BaseApiClient):
    # Maps indicator name -> (table_id, 10-part coordinate, 8-digit productId)
    INDICATORS: dict[str, tuple[str, str, int]] = {
        "cpi":          ("18-10-0004-01", "2.2.0.0.0.0.0.0.0.0", 18100004),
        "gdp":          ("36-10-0104-01", "1.1.1.30.0.0.0.0.0.0", 36100104),
        "unemployment": ("14-10-0287-01", "1.7.1.1.1.1.0.0.0.0", 14100287),
        "ippi":         ("18-10-0266-01", "1.1.0.0.0.0.0.0.0.0", 18100266),
        "retail_trade": ("20-10-0008-01", "1.1.2.0.0.0.0.0.0.0", 20100008),
    }

    def __init__(self) -> None:
        super().__init__(base_url=settings.statcan_base_url)

    async def fetch_indicator(self, table_id: str) -> list[StatCanObservation]:
        entry = next(
            ((coord, pid) for _, (tid, coord, pid) in self.INDICATORS.items() if tid == table_id),
            None,
        )
        if entry is None:
            raise ValueError(f"Unknown table_id: {table_id!r}")
        coordinate, product_id = entry
        path = "getDataFromCubePidCoordAndLatestNPeriods"
        raw: list[dict[str, Any]] = await self._post(
            path,
            body=[{"productId": product_id, "coordinate": coordinate, "latestN": 120}],
        )
        return self._parse(raw, table_id)

    def _parse(self, raw: list[dict[str, Any]], indicator_key: str) -> list[StatCanObservation]:
        if not raw:
            raise ValueError(f"Empty response for {indicator_key}")
        envelope = raw[0]
        if envelope.get("status") != "SUCCESS":
            raise ValueError(
                f"Unexpected status for {indicator_key}: {str(envelope)[:200]}"
            )
        obj = envelope.get("object", {})
        if obj.get("responseStatusCode") != 0:
            raise ValueError(
                f"Non-zero responseStatusCode for {indicator_key}: {str(obj)[:200]}"
            )
        points = obj.get("vectorDataPoint", [])
        now = datetime.now(tz=UTC)
        result = []
        for pt in points:
            if pt.get("value") is None:
                continue
            ref_date = date.fromisoformat(pt["refPer"][:10])
            # statusCode 0 = final ("A"), anything else = preliminary ("P")
            status = "A" if pt.get("statusCode") == 0 else "P"
            result.append(
                StatCanObservation(
                    indicator_key=indicator_key,
                    reference_date=ref_date,
                    value=Decimal(str(pt["value"])),
                    status=status,
                    ingested_at=now,
                )
            )
        return result

    async def fetch_all(self) -> list[StatCanObservation]:
        batches = await asyncio.gather(
            *[self.fetch_indicator(tid) for _, (tid, _, _) in self.INDICATORS.items()]
        )
        return [obs for batch in batches for obs in batch]
