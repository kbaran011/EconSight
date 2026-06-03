from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class BocObservation:
    series_key: str
    reference_date: date
    value: Decimal
    ingested_at: datetime
