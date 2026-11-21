"""Deterministic official closing-price reader.

The reader supports an identified local official-close export and an optional licensed desktop path:

1. A CSV export named by ``--export`` or ``LSEG_CLOSES_EXPORT``, with its exact source label.
2. An optional LSEG Workspace desktop session through ``lseg-data``.

It does not use a public price website as a fallback. Missing data is an
expected result and is reported as ``not available``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


EASTERN = ZoneInfo("America/New_York")
SOURCE_LSEG_EXPORT = "LSEG Workspace export"
SOURCE_LSEG_DESKTOP = "LSEG Workspace desktop session"


@dataclass(frozen=True, order=True)
class CloseRecord:
    """One official daily close from a licensed source."""

    pricing_date: date
    instrument: str
    close: Decimal
    currency: str
    source: str
    volume: Decimal | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {
            "pricing_date": self.pricing_date.isoformat(),
            "instrument": self.instrument,
            "close": format(self.close, "f"),
            "currency": self.currency,
            "source": self.source,
        }
        if self.volume is not None:
            payload["volume"] = format(self.volume, "f")
        return payload


@dataclass(frozen=True)
class CloseReaderResult:
    """A data result that can finish cleanly when licensed data is absent."""

    status: str
    records: tuple[CloseRecord, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "records": [record.to_dict() for record in self.records],
            "message": self.message,
        }


def _normalise_heading(value: Any) -> str:
    if isinstance(value, tuple):
        value = "_".join(str(part) for part in value if part not in (None, ""))
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _select_key(keys: Iterable[Any], exact: Sequence[str], contains: Sequence[str] = ()) -> Any | None:
    normalised = [(key, _normalise_heading(key)) for key in keys]
    for target in exact:
        for original, clean in normalised:
            if clean == target:
                return original
    for fragment in contains:
        for original, clean in normalised:
            if fragment in clean:
                return original
    return None


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("The close row has no pricing date.")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"Invalid pricing date: {text!r}.") from exc


def _parse_close(value: Any) -> Decimal:
    text = str(value).strip().replace(",", "")
    try:
        close = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid closing price: {value!r}.") from exc
    if not close.is_finite() or close <= 0:
        raise ValueError(f"Closing price must be positive and finite: {value!r}.")
    return close


def _parse_volume(value: Any) -> Decimal:
    text = str(value).strip().replace(",", "")
    try:
        volume = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid trading volume: {value!r}.") from exc
    if not volume.is_finite() or volume < 0:
        raise ValueError(f"Trading volume must be nonnegative and finite: {value!r}.")
    return volume


def _records_from_rows(
    rows: Iterable[Mapping[Any, Any]],
    requested_instrument: str,
    source: str,
) -> list[CloseRecord]:
    raw_rows = list(rows)
    if not raw_rows:
        return []
    keys = list(raw_rows[0].keys())
    date_key = _select_key(
        keys,
        ("date", "pricing_date", "trade_date", "price_date"),
        ("priceclose_date", "price_close_date"),
    )
    close_key = _select_key(
        keys,
        ("close", "official_close", "price_close", "tr_priceclose", "trdprc_1"),
        ("priceclose", "closing_price"),
    )
    instrument_key = _select_key(keys, ("instrument", "ric", "ticker", "symbol", "universe"))
    currency_key = _select_key(keys, ("currency", "currency_code", "ccy"))
    volume_key = _select_key(
        keys,
        ("volume", "tr_volume", "trading_volume", "daily_volume"),
        ("tr_volume", "trading_volume", "daily_volume"),
    )
    if date_key is None or close_key is None:
        raise ValueError("The price source must contain a date column and an official close column.")

    requested = requested_instrument.strip().upper()
    by_date: dict[date, CloseRecord] = {}
    for row in raw_rows:
        row_instrument = str(row.get(instrument_key, requested)).strip().upper() if instrument_key else requested
        if row_instrument and row_instrument != requested:
            continue
        raw_date = row.get(date_key)
        raw_close = row.get(close_key)
        if raw_date in (None, "") or raw_close in (None, ""):
            continue
        raw_volume = row.get(volume_key) if volume_key is not None else None
        pricing_date = _parse_date(raw_date)
        record = CloseRecord(
            pricing_date=pricing_date,
            instrument=requested,
            close=_parse_close(raw_close),
            currency=str(row.get(currency_key, "")).strip().upper() if currency_key else "",
            source=source,
            volume=_parse_volume(raw_volume) if raw_volume not in (None, "") else None,
        )
        prior = by_date.get(pricing_date)
        if prior and (prior.close != record.close or prior.volume != record.volume):
            raise ValueError(
                f"Conflicting closes or volumes for {requested} on {pricing_date.isoformat()}."
            )
        by_date[pricing_date] = record
    return sorted(by_date.values())


def _read_export(path: Path, instrument: str, source: str = SOURCE_LSEG_EXPORT) -> list[CloseRecord]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Licensed close export not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel
        return _records_from_rows(csv.DictReader(handle, dialect=dialect), instrument, source)


def _frame_rows(frame: Any) -> list[dict[Any, Any]]:
    if frame is None or getattr(frame, "empty", False):
        return []
    reset = frame.reset_index() if hasattr(frame, "reset_index") else frame
    if hasattr(reset, "to_dict"):
        return list(reset.to_dict(orient="records"))
    raise ValueError("LSEG returned an unsupported table type.")


def _read_lseg_desktop(
    instrument: str,
    start_date: date,
    end_date: date,
    app_key: str,
) -> list[CloseRecord]:
    try:
        import lseg.data as ld
    except ImportError as exc:
        raise RuntimeError("The optional lseg-data package is not installed.") from exc

    session_kwargs: dict[str, str] = {"name": "desktop.workspace"}
    if app_key:
        session_kwargs["app_key"] = app_key
    opened = False
    try:
        ld.open_session(**session_kwargs)
        opened = True
        frame = ld.get_data(
            universe=[instrument],
            fields=["TR.PriceClose.date", "TR.PriceClose", "TR.PriceClose.currency", "TR.Volume"],
            parameters={
                "SDate": start_date.isoformat(),
                "EDate": end_date.isoformat(),
                "Frq": "D",
            },
        )
        return _records_from_rows(_frame_rows(frame), instrument, SOURCE_LSEG_DESKTOP)
    finally:
        if opened:
            close = getattr(ld, "close_session", None)
            if callable(close):
                close()


def official_daily_closes(
    instrument: str,
    start_date: date | str,
    end_date: date | str,
    *,
    export_path: Path | str | None = None,
    export_source: str = SOURCE_LSEG_EXPORT,
    app_key: str | None = None,
) -> CloseReaderResult:
    """Return official daily closes for an inclusive date range."""

    clean_instrument = instrument.strip().upper()
    if not clean_instrument:
        raise ValueError("Instrument is required.")
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise ValueError("End date must be on or after start date.")

    configured_export = export_path or os.getenv("LSEG_CLOSES_EXPORT", "").strip()
    try:
        if configured_export:
            clean_source = export_source.strip()
            if not clean_source:
                raise ValueError("The export source label must not be blank.")
            records = _read_export(Path(configured_export).expanduser(), clean_instrument, clean_source)
        else:
            records = _read_lseg_desktop(
                clean_instrument,
                start,
                end,
                (app_key if app_key is not None else os.getenv("LSEG_APP_KEY", "")).strip(),
            )
    except (FileNotFoundError, RuntimeError) as exc:
        return CloseReaderResult(status="not available", records=(), message=str(exc))
    except Exception as exc:
        return CloseReaderResult(
            status="not available",
            records=(),
            message=f"Licensed closing-price request failed: {type(exc).__name__}: {exc}",
        )

    selected = tuple(record for record in records if start <= record.pricing_date <= end)
    if not selected:
        return CloseReaderResult(
            status="not available",
            records=(),
            message=(
                f"No official daily close was available for {clean_instrument} from "
                f"{start.isoformat()} through {end.isoformat()}."
            ),
        )
    return CloseReaderResult(status="available", records=selected, message="")


def parse_filed_datetime(value: str | datetime) -> datetime:
    """Parse an EDGAR Accepted time and express it in U.S. Eastern time."""

    if isinstance(value, datetime):
        parsed = value
    else:
        text = value.strip()
        if not text:
            raise ValueError("Filed datetime is required.")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("Filed datetime must use ISO 8601 format.") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=EASTERN)
    return parsed.astimezone(EASTERN)


def last_close_before(
    instrument: str,
    filed_at: str | datetime,
    *,
    export_path: Path | str | None = None,
    export_source: str = SOURCE_LSEG_EXPORT,
    app_key: str | None = None,
    lookback_days: int = 14,
) -> CloseReaderResult:
    """Return the last regular 4:00 PM Eastern close before a filing time."""

    if lookback_days < 1:
        raise ValueError("Lookback days must be at least 1.")
    filed = parse_filed_datetime(filed_at)
    start = date.fromordinal(filed.date().toordinal() - lookback_days)
    daily = official_daily_closes(
        instrument,
        start,
        filed.date(),
        export_path=export_path,
        export_source=export_source,
        app_key=app_key,
    )
    if daily.status != "available":
        return daily
    eligible = [
        record
        for record in daily.records
        if datetime.combine(record.pricing_date, time(16, 0), tzinfo=EASTERN) < filed
    ]
    if not eligible:
        return CloseReaderResult(
            status="not available",
            records=(),
            message=f"No regular close before {filed.isoformat()} was available for {instrument.upper()}.",
        )
    return CloseReaderResult(status="available", records=(eligible[-1],), message="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read licensed official daily closing prices.")
    parser.add_argument("instrument", help="LSEG RIC or the instrument label used in the export")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--filed", help="Return the last 4:00 PM Eastern close before this ISO datetime")
    mode.add_argument("--start", help="Inclusive start date for a daily range, YYYY-MM-DD")
    parser.add_argument("--end", help="Inclusive range end date; required with --start")
    parser.add_argument("--export", type=Path, help="Licensed local CSV export; overrides LSEG_CLOSES_EXPORT")
    parser.add_argument(
        "--export-source",
        default=SOURCE_LSEG_EXPORT,
        help="Exact source label for a local official-close export",
    )
    parser.add_argument("--lookback-days", type=int, default=14, help="Calendar-day lookback for --filed")
    return parser


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    args = build_parser().parse_args()
    try:
        if args.filed:
            result = last_close_before(
                args.instrument,
                args.filed,
                export_path=args.export,
                export_source=args.export_source,
                lookback_days=args.lookback_days,
            )
        else:
            if not args.end:
                raise ValueError("--end is required with --start.")
            result = official_daily_closes(
                args.instrument,
                args.start,
                args.end,
                export_path=args.export,
                export_source=args.export_source,
            )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
