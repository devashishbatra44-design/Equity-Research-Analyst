"""SEC index and filing-folder helpers for the Week 4 spinoff seeker."""

from __future__ import annotations

import json
import gzip
import time
import urllib.request
import zlib
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import PurePosixPath
from typing import Any, Callable, Iterator, Mapping


SEC_ARCHIVES = "https://www.sec.gov/Archives"
SEC_DATA = "https://data.sec.gov"
FORM10_FORMS = {"10-12B", "10-12B/A", "10-12G", "10-12G/A", "CERT"}


@dataclass(frozen=True)
class IndexFiling:
    cik: str
    company_name: str
    form: str
    filed_date: date
    filename: str

    @property
    def accession(self) -> str:
        return PurePosixPath(self.filename).stem

    @property
    def filing_url(self) -> str:
        return f"{SEC_ARCHIVES}/{self.filename}"

    @property
    def folder_index_url(self) -> str:
        return f"{SEC_ARCHIVES}/{PurePosixPath(self.filename).parent}/index.json"


class SecClient:
    """Small SEC client with a declared User-Agent and a sub-10/sec limit."""

    def __init__(
        self,
        user_agent: str,
        *,
        min_interval_seconds: float = 0.11,
        opener: Callable[..., Any] = urllib.request.urlopen,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if "@" not in user_agent or len(user_agent.strip()) < 8:
            raise ValueError("SEC User-Agent must identify a person or team and an email address.")
        if min_interval_seconds < 0.1:
            raise ValueError("SEC interval must remain below 10 requests per second.")
        self.user_agent = user_agent.strip()
        self.min_interval_seconds = min_interval_seconds
        self.opener = opener
        self.clock = clock
        self.sleeper = sleeper
        self._last_request: float | None = None

    def get_bytes(self, url: str) -> bytes:
        now = self.clock()
        if self._last_request is not None:
            wait = self.min_interval_seconds - (now - self._last_request)
            if wait > 0:
                self.sleeper(wait)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": urlparse(url).netloc,
            },
        )
        with self.opener(request, timeout=30) as response:
            body = response.read()
            headers = getattr(response, "headers", {})
            encoding = str(headers.get("Content-Encoding", "")).lower() if hasattr(headers, "get") else ""
            if encoding == "gzip":
                body = gzip.decompress(body)
            elif encoding == "deflate":
                body = zlib.decompress(body)
        self._last_request = self.clock()
        return body

    def get_text(self, url: str) -> str:
        return self.get_bytes(url).decode("utf-8", errors="replace")

    def get_json(self, url: str) -> Mapping[str, Any]:
        value = json.loads(self.get_text(url))
        if not isinstance(value, Mapping):
            raise ValueError(f"SEC response was not a JSON object: {url}")
        return value


def quarter(day: date) -> int:
    return (day.month - 1) // 3 + 1


def master_index_url(day: date) -> str:
    return (
        f"{SEC_ARCHIVES}/edgar/daily-index/{day.year}/QTR{quarter(day)}/"
        f"master.{day:%Y%m%d}.idx"
    )


def parse_master_index(text: str) -> tuple[IndexFiling, ...]:
    rows: list[IndexFiling] = []
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) != 5 or not parts[0].strip().isdigit():
            continue
        cik, company_name, form, filed, filename = (part.strip() for part in parts)
        try:
            filed_date = date.fromisoformat(filed)
        except ValueError:
            continue
        rows.append(IndexFiling(cik, company_name, form, filed_date, filename))
    return tuple(rows)


def iter_dates(start: date, end: date) -> Iterator[date]:
    if end < start:
        raise ValueError("End date must be on or after start date.")
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def form10_candidates(client: SecClient, start: date, end: date) -> tuple[IndexFiling, ...]:
    """Read the SEC daily master indexes for Form 10 and certification filings."""

    candidates: list[IndexFiling] = []
    for day in iter_dates(start, end):
        if day.weekday() >= 5:
            continue
        try:
            rows = parse_master_index(client.get_text(master_index_url(day)))
        except Exception as exc:
            if getattr(exc, "code", None) == 404:
                continue
            raise
        candidates.extend(row for row in rows if row.form.upper() in FORM10_FORMS)
    return tuple(candidates)


def filing_folder_documents(client: SecClient, filing: IndexFiling) -> tuple[str, ...]:
    """Return every named document in the filing folder without guessing exhibits."""

    payload = client.get_json(filing.folder_index_url)
    items = payload.get("directory", {}).get("item", [])
    if not isinstance(items, list):
        raise ValueError("SEC filing folder has no item list.")
    base = filing.folder_index_url.removesuffix("index.json")
    return tuple(f"{base}{item['name']}" for item in items if isinstance(item, Mapping) and item.get("name"))


def parent_recent_8ks(client: SecClient, parent_cik: str) -> tuple[IndexFiling, ...]:
    """Return recent parent 8-K candidates for a human distribution check."""

    cik = parent_cik.strip().zfill(10)
    payload = client.get_json(f"{SEC_DATA}/submissions/CIK{cik}.json")
    recent = payload.get("filings", {}).get("recent", {})
    if not isinstance(recent, Mapping):
        raise ValueError("SEC submissions response has no recent filings table.")
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    name = str(payload.get("name", ""))
    rows: list[IndexFiling] = []
    for form, accession, filed, primary in zip(forms, accessions, filing_dates, primary_docs):
        if str(form).upper() != "8-K":
            continue
        accession_compact = str(accession).replace("-", "")
        filename = f"edgar/data/{int(cik)}/{accession_compact}/{primary}"
        rows.append(IndexFiling(cik, name, "8-K", date.fromisoformat(str(filed)), filename))
    return tuple(rows)
