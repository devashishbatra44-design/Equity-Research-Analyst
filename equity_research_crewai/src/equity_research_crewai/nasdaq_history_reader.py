"""Normalize a saved Nasdaq official historical-price response."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
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


def summarize(normalized: Mapping[str, Any], *, session_count: int = 30) -> dict[str, Any]:
    """Return derived market metrics without copying the close list."""

    if session_count < 1:
        raise ValueError("Session count must be at least 1.")
    records = normalized.get("records", [])
    if not isinstance(records, list) or not records:
        return {
            "status": "not available",
            "source": normalized.get("source"),
            "source_url": normalized.get("source_url"),
            "observation_count": 0,
        }
    selected = records[-session_count:]
    dollar_volumes = [
        _decimal(record["close"]) * _decimal(record["volume"])
        for record in selected
    ]
    latest = selected[-1]
    return {
        "status": "available",
        "source": normalized.get("source"),
        "source_url": normalized.get("source_url"),
        "source_sha256": normalized.get("source_sha256"),
        "instrument": latest["instrument"],
        "currency": latest["currency"],
        "observation_count": len(selected),
        "requested_session_count": session_count,
        "available_session_count": len(records),
        "start_date": selected[0]["pricing_date"],
        "end_date": latest["pricing_date"],
        "end_date_close": latest["close"],
        "end_date_volume": latest["volume"],
        "median_daily_dollar_volume": format(Decimal(str(median(dollar_volumes))), "f"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()

    raw_bytes = args.input.read_bytes()
    payload = json.loads(raw_bytes.decode("utf-8"))
    result = normalize(payload, args.instrument, args.source_url)
    result["source_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(
            json.dumps(summarize(result), indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
