"""Week 4 live-record reaction and hit-rate calculations and table output."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
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


def last_close_before_filing(filed_at: str | datetime, closes: Sequence[CloseRecord]) -> CloseRecord | None:
    filed = parse_filed_datetime(filed_at)
    eligible = [
        record
        for record in closes
        if datetime.combine(record.pricing_date, time(16, 0), tzinfo=EASTERN) < filed
    ]
    return max(eligible, default=None)


def _parse_records(payload: dict[str, object], ticker: str) -> tuple[CloseRecord, ...]:
    raw_records = payload.get("records", [])
    if not isinstance(raw_records, list):
        raise ValueError("The closes file must contain a records list.")
    records: list[CloseRecord] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise ValueError("Each close record must be an object.")
        instrument = str(raw.get("instrument", "")).upper()
        if instrument != ticker.upper():
            continue
        records.append(
            CloseRecord(
                pricing_date=datetime.fromisoformat(str(raw["pricing_date"])).date(),
                instrument=instrument,
                close=Decimal(str(raw["close"])),
                currency=str(raw.get("currency", "")),
                source=str(raw.get("source", "")),
                volume=Decimal(str(raw["volume"])) if raw.get("volume") not in (None, "") else None,
            )
        )
    return tuple(sorted(records))


def _agreement(direction: str, reaction: Decimal | None) -> str:
    if direction == "not computed" or reaction is None:
        return "not computed"
    positive = direction in {"up", "more"}
    negative = direction in {"down", "less"}
    if not (positive or negative):
        raise ValueError(f"Unsupported view direction: {direction!r}.")
    agrees = (positive and reaction > 0) or (negative and reaction < 0)
    return "agree" if agrees else "disagree"


def row_from_saved_run(run_dir: Path) -> HitRateRow:
    view_path = run_dir / "hit_rate_view.json"
    closes_path = run_dir / "hit_rate_closes.json"
    view = json.loads(view_path.read_text(encoding="utf-8"))
    ticker = str(view["ticker"]).upper()
    closes = _parse_records(json.loads(closes_path.read_text(encoding="utf-8")), ticker)
    before = last_close_before_filing(str(view["filing_time"]), closes)
    after_close = first_close_after_filing(str(view["filing_time"]), closes)
    reaction = reaction_percent(before, after_close) if before and after_close else None
    view_time = parse_filed_datetime(str(view["view_time"]))
    after_flag = bool(
        after_close
        and view_time > datetime.combine(after_close.pricing_date, time(16, 0), tzinfo=EASTERN)
    )
    direction = str(view["direction"])
    return HitRateRow(
        ticker=ticker,
        filing_time=str(view["filing_time"]),
        view_time=str(view["view_time"]),
        direction=direction,
        reaction=reaction,
        agreement=_agreement(direction, reaction),
        after=after_flag,
    )


def render_table(rows: Sequence[HitRateRow]) -> str:
    lines = [
        "# Hit-rate table",
        "",
        "| Ticker | Filing time | View time | Direction | Reaction | Result | After? |",
        "|---|---|---|---|---:|---|---|",
    ]
    for row in rows:
        reaction = "not computed" if row.reaction is None else f"{row.reaction:.4f}%"
        lines.append(
            f"| {row.ticker} | {row.filing_time} | {row.view_time} | {row.direction} | "
            f"{reaction} | {row.agreement} | {'after' if row.after else 'no'} |"
        )
    result = summarize(rows)
    lines.extend(
        [
            "",
            (
                f"Scored: {result['scored']}; agreements: {result['agreed']}; "
                f"disagreements: {result['disagreed']}; hit rate: {result['hit_rate']}."
            ),
            "",
            "Rows marked `after` and views marked `not computed` are excluded from the scored count.",
        ]
    )
    return "\n".join(lines) + "\n"


def summarize(rows: Sequence[HitRateRow]) -> dict[str, int | str]:
    scored = [row for row in rows if not row.after and row.reaction is not None and row.direction != "not computed"]
    agreed = sum(row.agreement == "agree" for row in scored)
    return {
        "scored": len(scored),
        "agreed": agreed,
        "disagreed": len(scored) - agreed,
        "hit_rate": "not computed" if not scored else f"{Decimal(agreed) / Decimal(len(scored)):.4f}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run_dirs = sorted(path.parent for path in args.runs_dir.glob("*/hit_rate_view.json"))
    rows = [row_from_saved_run(run_dir) for run_dir in run_dirs]
    text = render_table(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
