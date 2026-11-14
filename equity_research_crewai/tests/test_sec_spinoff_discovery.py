from __future__ import annotations

import json
import urllib.request
from datetime import date

import pytest

from equity_research_crewai.sec_spinoff_discovery import (
    IndexFiling,
    SecClient,
    filing_folder_documents,
    form10_candidates,
    master_index_url,
    parent_recent_8ks,
    parse_master_index,
)


class Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_sec_client_declares_user_agent_and_throttles() -> None:
    requests: list[urllib.request.Request] = []
    sleeps: list[float] = []
    times = iter([1.0, 1.0, 1.05, 1.16])

    def opener(request: urllib.request.Request, timeout: int) -> Response:
        assert timeout == 30
        requests.append(request)
        return Response(b"ok")

    client = SecClient("DJS Team team@example.edu", opener=opener, clock=lambda: next(times), sleeper=sleeps.append)
    client.get_text("https://www.sec.gov/a")
    client.get_text("https://www.sec.gov/b")
    assert requests[0].headers["User-agent"] == "DJS Team team@example.edu"
    assert sleeps == [pytest.approx(0.06)]


def test_master_index_parser_keeps_form_and_filing_folder() -> None:
    text = "CIK|Company Name|Form Type|Date Filed|Filename\n1|Child Co|10-12B|2026-11-10|edgar/data/1/0001/test.txt\n"
    row = parse_master_index(text)[0]
    assert row.form == "10-12B"
    assert row.folder_index_url.endswith("edgar/data/1/0001/index.json")


def test_form10_candidates_reads_business_days_and_keeps_amendments() -> None:
    payload = b"1|Child Co|10-12B/A|2026-11-09|edgar/data/1/0001/test.txt\n2|Other|8-K|2026-11-09|edgar/data/2/0002/test.txt\n"
    client = SecClient("DJS Team team@example.edu", opener=lambda *_args, **_kwargs: Response(payload))
    rows = form10_candidates(client, date(2026, 11, 9), date(2026, 11, 9))
    assert [row.form for row in rows] == ["10-12B/A"]
    assert master_index_url(date(2026, 11, 9)).endswith("2026/QTR4/master.20261109.idx")


def test_filing_folder_returns_all_named_documents() -> None:
    body = json.dumps({"directory": {"item": [{"name": "form10.htm"}, {"name": "exhibit991.htm"}]}}).encode()
    client = SecClient("DJS Team team@example.edu", opener=lambda *_args, **_kwargs: Response(body))
    filing = IndexFiling("1", "Child", "10-12B", date(2026, 11, 9), "edgar/data/1/0001/form10.txt")
    assert filing_folder_documents(client, filing) == (
        "https://www.sec.gov/Archives/edgar/data/1/0001/form10.htm",
        "https://www.sec.gov/Archives/edgar/data/1/0001/exhibit991.htm",
    )


def test_parent_recent_8ks_uses_parent_cik() -> None:
    payload = {
        "name": "Parent Co",
        "filings": {"recent": {"form": ["8-K", "10-Q"], "accessionNumber": ["0001-26-000001", "0001-26-000002"], "filingDate": ["2026-11-10", "2026-11-09"], "primaryDocument": ["p8k.htm", "q.htm"]}},
    }
    client = SecClient("DJS Team team@example.edu", opener=lambda *_args, **_kwargs: Response(json.dumps(payload).encode()))
    rows = parent_recent_8ks(client, "1")
    assert len(rows) == 1
    assert rows[0].company_name == "Parent Co"
    assert rows[0].filing_url.endswith("/1/000126000001/p8k.htm")


def test_sec_user_agent_requires_email() -> None:
    with pytest.raises(ValueError, match="email"):
        SecClient("anonymous")
