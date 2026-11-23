"""Audit frozen F1 with official Nasdaq historical regular closes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.parse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from .closes_reader import CloseRecord, close_records_from_rows
from .spinoff_seeker import (
    child_market_cap_is_small,
    child_parent_market_cap_ratio_from_distribution,
)


NASDAQ_API = "https://api.nasdaq.com/api/quote/{ticker}/historical"


def _decimal(value: object) -> Decimal:
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if not cleaned:
        raise ValueError(f"Invalid close value: {value}")
    return Decimal(cleaned)


def parse_historical_rows(payload: Mapping[str, Any], ticker: str) -> tuple[CloseRecord, ...]:
    """Route Nasdaq's official historical table through the common closes reader."""

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return ()
    trades_table = data.get("tradesTable")
    if not isinstance(trades_table, Mapping):
        return ()
    rows = trades_table.get("rows", [])
    if not isinstance(rows, list):
        return ()
    parsed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping) or not row.get("date") or not row.get("close"):
            continue
        parsed.append(
            {
                "instrument": ticker,
                "date": date.fromisoformat(
                    f"{str(row['date']).split('/')[2]}-{int(str(row['date']).split('/')[0]):02d}-{int(str(row['date']).split('/')[1]):02d}"
                ).isoformat(),
                "close": str(_decimal(row["close"])),
                "currency": "USD",
            }
        )
    return close_records_from_rows(parsed, ticker, "Nasdaq official historical endpoint")


def historical_url(ticker: str, start: date, end: date) -> str:
    query = urllib.parse.urlencode(
        {
            "assetclass": "stocks",
            "fromdate": start.isoformat(),
            "todate": end.isoformat(),
            "limit": "5000",
        }
    )
    return f"{NASDAQ_API.format(ticker=ticker.upper())}?{query}"


def fetch_history(ticker: str, start: date, end: date) -> tuple[tuple[CloseRecord, ...], str]:
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker.upper()):
        raise ValueError(f"Invalid ticker: {ticker}")
    url = historical_url(ticker, start, end)
    completed = subprocess.run(
        [
            "curl",
            "--http1.1",
            "-L",
            "-sS",
            "-A",
            "Mozilla/5.0",
            url,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )
    payload = json.loads(completed.stdout)
    return parse_historical_rows(payload, ticker), url


def first_after(rows: Sequence[CloseRecord], target: date) -> CloseRecord | None:
    return next((row for row in rows if row.pricing_date > target), None)


def on_date(rows: Sequence[CloseRecord], target: date) -> CloseRecord | None:
    return next((row for row in rows if row.pricing_date == target), None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit F1 from official Nasdaq regular closes.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _json_value(value: object) -> object:
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {value!r}")


def main() -> None:
    args = build_parser().parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    distribution_dates = [
        date.fromisoformat(entry["distribution_date"])
        for entry in registry["included_distributions"]
    ]
    start = date(min(value.year for value in distribution_dates), 1, 1)
    end = date.fromisoformat(registry["index_date"])
    cache: dict[str, tuple[tuple[CloseRecord, ...], str]] = {}
    results: list[dict[str, Any]] = []
    for entry in registry["included_distributions"]:
        child_ticker = entry.get("child_ticker")
        parent_ticker = entry.get("parent_ticker")
        distributed = date.fromisoformat(entry["distribution_date"])
        regular_start = (
            date.fromisoformat(entry["regular_trading_start_date"])
            if entry.get("regular_trading_start_date")
            else None
        )
        result: dict[str, Any] = {
            "child": entry["child"],
            "parent": entry["parent"],
            "distribution_date": distributed,
            "regular_trading_start_date": regular_start,
            "child_ticker": child_ticker,
            "parent_ticker": parent_ticker,
            "child_close": None,
            "parent_close": None,
            "pricing_date": None,
            "market_cap_ratio": None,
            "f1": None,
            "data_limit": None,
            "sources": [],
        }
        if not child_ticker:
            result["data_limit"] = entry.get("data_limit") or "Required child ticker is unavailable."
            results.append(result)
            continue
        try:
            if child_ticker not in cache:
                cache[child_ticker] = fetch_history(child_ticker, start, end)
            child_rows, child_url = cache[child_ticker]
            child_close = first_after(child_rows, distributed)
            if child_close is None:
                result["data_limit"] = "No official regular close was returned on or after distribution."
                result["sources"] = [child_url]
                results.append(result)
                continue
            result["child_close"] = child_close.close
            result["pricing_date"] = child_close.pricing_date
            if not parent_ticker:
                result["sources"] = [child_url]
                result["data_limit"] = entry.get("data_limit") or "Required parent ticker is unavailable."
                results.append(result)
                continue
            if parent_ticker not in cache:
                cache[parent_ticker] = fetch_history(parent_ticker, start, end)
            parent_rows, parent_url = cache[parent_ticker]
            parent_close = on_date(parent_rows, child_close.pricing_date)
            result["sources"] = [child_url, parent_url]
            if parent_close is None:
                result["data_limit"] = "No same-date official parent close was returned."
                results.append(result)
                continue
            result["parent_close"] = parent_close.close
            ratio = child_parent_market_cap_ratio_from_distribution(
                Decimal(entry["distributed_child_shares_per_parent_share"])
                if entry.get("distributed_child_shares_per_parent_share") is not None
                else None,
                Decimal(entry["fraction_distributed"]) if entry.get("fraction_distributed") else None,
                child_close.close,
                parent_close.close,
            )
            result["market_cap_ratio"] = ratio
            result["f1"] = child_market_cap_is_small(ratio, Decimal("1"))
            if ratio is None:
                result["data_limit"] = "Required distribution term is missing."
        except Exception as exc:
            result["data_limit"] = f"Official-close retrieval failed: {type(exc).__name__}."
        results.append(result)
        print(f"Reviewed F1 for {entry['child']}.", flush=True)
    payload = {
        "source": "Nasdaq official historical endpoint; regular ticker only",
        "currency": "USD",
        "window_start": start,
        "index_date": end,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=_json_value) + "\n", encoding="utf-8")
    print(f"Saved {len(results)} F1 audits to {args.output}.")


if __name__ == "__main__":
    main()
