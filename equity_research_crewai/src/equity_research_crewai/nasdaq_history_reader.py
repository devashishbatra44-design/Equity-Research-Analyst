"""Normalize a saved Nasdaq official historical-price response."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping


def _decimal(value: object) -> Decimal:
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if not cleaned:
        raise ValueError(f"Invalid numeric value: {value!r}")
    result = Decimal(cleaned)
    if not result.is_finite():
        raise ValueError(f"Non-finite numeric value: {value!r}")
    return result


def normalize(payload: Mapping[str, Any], instrument: str, source_url: str) -> dict[str, Any]:
    table = payload.get("data", {}).get("tradesTable", {})
    rows = table.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("Nasdaq response has no historical rows list.")

    records: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if not row.get("date") or not row.get("close") or row.get("volume") in (None, ""):
            continue
        pricing_date = datetime.strptime(str(row["date"]), "%m/%d/%Y").date().isoformat()
        close = _decimal(row["close"])
        volume = _decimal(row["volume"])
        if close <= 0 or volume < 0:
            raise ValueError(f"Invalid close or volume for {pricing_date}.")
        records.append(
            {
                "instrument": instrument.upper(),
                "pricing_date": pricing_date,
                "close": str(close),
                "volume": str(volume),
                "currency": "USD",
                "source": "Nasdaq official historical endpoint",
            }
        )

    records.sort(key=lambda record: record["pricing_date"])
    return {
        "status": "available" if records else "not available",
        "source": "Nasdaq official historical endpoint",
        "source_url": source_url,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = normalize(payload, args.instrument, args.source_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
