"""Week 4 live-record reaction and hit-rate calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from typing import Sequence

from .closes_reader import EASTERN, CloseRecord, parse_filed_datetime


@dataclass(frozen=True)
class HitRateRow:
    ticker: str
    filing_time: str
    view_time: str
    direction: str
    reaction: Decimal | None
    agreement: str
    after: bool


def reaction_percent(before: CloseRecord, after: CloseRecord) -> Decimal:
    if after.pricing_date <= before.pricing_date:
        raise ValueError("The reaction close must be after the pre-filing close.")
    return (after.close / before.close - Decimal("1")) * Decimal("100")


def first_close_after_filing(filed_at: str | datetime, closes: Sequence[CloseRecord]) -> CloseRecord | None:
    filed = parse_filed_datetime(filed_at)
    eligible = [
        record
        for record in closes
        if datetime.combine(record.pricing_date, time(16, 0), tzinfo=EASTERN) > filed
    ]
    return min(eligible, default=None)


def summarize(rows: Sequence[HitRateRow]) -> dict[str, int | str]:
    scored = [row for row in rows if not row.after and row.reaction is not None and row.direction != "not computed"]
    agreed = sum(row.agreement == "agree" for row in scored)
    return {
        "scored": len(scored),
        "agreed": agreed,
        "disagreed": len(scored) - agreed,
        "hit_rate": "not computed" if not scored else f"{Decimal(agreed) / Decimal(len(scored)):.4f}",
    }
