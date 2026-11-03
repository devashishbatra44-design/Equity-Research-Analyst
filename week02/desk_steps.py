#!/usr/bin/env python3
"""Build the seven-step SEC data layer for an equity-research desk.

The program makes no model calls. It stores every financial claim with its SEC
source, filing, period, unit, and XBRL tag. It never stores or prints the SEC
User-Agent.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup, NavigableString
from dotenv import load_dotenv


PROGRAM_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = Path(__file__).resolve().parent / "runs"

SEC_WWW = "https://www.sec.gov"
SEC_DATA = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
COMPANY_TICKERS_URL = f"{SEC_WWW}/files/company_tickers.json"

STEP_NAMES = {
    1: "Resolve the ticker",
    2: "Select the filings",
    3: "Download and convert the documents",
    4: "Retrieve annual XBRL company facts",
    5: "Calculate financial measures",
    6: "Extract quarterly revenue and diluted EPS",
    7: "Process the peers",
}

# Ordered lists are intentional. Earlier tags win only after period coverage and
# recency tests tie. Total revenue precedes net-sales tags.
CONCEPTS: OrderedDict[str, dict[str, Any]] = OrderedDict(
    {
        "total_revenue": {
            "label": "Total revenue",
            "kind": "duration",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": (
                "Revenues",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",
            ),
        },
        "operating_income": {
            "label": "Operating income",
            "kind": "duration",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": ("OperatingIncomeLoss",),
        },
        "net_income": {
            "label": "Net income",
            "kind": "duration",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": ("NetIncomeLoss", "ProfitLoss"),
        },
        "diluted_eps": {
            "label": "Diluted earnings per share",
            "kind": "duration",
            "unit_keys": ("USD/shares", "USD/share"),
            "unit": "USD/share",
            "tags": ("EarningsPerShareDiluted",),
        },
        "stockholders_equity": {
            "label": "Stockholders' equity",
            "kind": "instant",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": (
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ),
        },
        "long_term_debt": {
            "label": "Long-term debt",
            "kind": "instant",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": (
                "LongTermDebtNoncurrent",
                "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
                "LongTermDebt",
            ),
        },
        "current_long_term_debt": {
            "label": "Current portion of long-term debt",
            "kind": "instant",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": (
                "LongTermDebtCurrent",
                "LongTermDebtAndFinanceLeaseObligationsCurrent",
                "CurrentPortionOfLongTermDebt",
            ),
        },
        "cash_from_operations": {
            "label": "Net cash provided by operating activities",
            "kind": "duration",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": ("NetCashProvidedByUsedInOperatingActivities",),
        },
        "property_equipment_additions": {
            "label": "Additions to property and equipment",
            "kind": "duration",
            "unit_keys": ("USD",),
            "unit": "USD",
            "tags": (
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsForAdditionsToPropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
            ),
        },
    }
)


class DeskError(RuntimeError):
    """A clear, expected pipeline failure."""


@dataclass
class Company:
    ticker: str
    name: str
    cik: int

    @property
    def cik10(self) -> str:
        return f"{self.cik:010d}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "legal_name": self.name,
            "cik": self.cik,
            "cik_10_digit": self.cik10,
        }


class SECClient:
    """A rate-limited SEC client with bounded retries."""

    def __init__(self, user_agent: str) -> None:
        if not user_agent.strip():
            raise DeskError("SEC_USER_AGENT is missing or empty in .env.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent.strip(),
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, text/html, text/plain, */*",
            }
        )
        self.minimum_interval = 0.20
        self.last_request_at = 0.0

    def get(self, url: str) -> requests.Response:
        last_message = "unknown SEC request failure"
        for attempt in range(1, 4):
            elapsed = time.monotonic() - self.last_request_at
            if elapsed < self.minimum_interval:
                time.sleep(self.minimum_interval - elapsed)
            try:
                response = self.session.get(url, timeout=30)
                self.last_request_at = time.monotonic()
            except requests.RequestException as exc:
                last_message = f"{type(exc).__name__}: {exc}"
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))
                    continue
                raise DeskError(f"SEC request failed after 3 attempts: {url}. {last_message}") from exc

            if response.status_code == 403:
                raise DeskError(
                    "SEC returned HTTP 403. Confirm that SEC_USER_AGENT contains your name "
                    "and email, then wait before retrying."
                )
            if response.status_code == 429 or 500 <= response.status_code < 600:
                last_message = f"HTTP {response.status_code}"
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))
                    continue
                raise DeskError(f"SEC request failed after 3 attempts: {url}. {last_message}")
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise DeskError(f"SEC request failed with HTTP {response.status_code}: {url}") from exc
            return response
        raise DeskError(f"SEC request failed: {url}. {last_message}")

    def json(self, url: str) -> Any:
        try:
            return self.get(url).json()
        except ValueError as exc:
            raise DeskError(f"SEC returned invalid JSON: {url}") from exc

    def text(self, url: str) -> str:
        response = self.get(url)
        response.encoding = response.encoding or "utf-8"
        return response.text


def load_sec_user_agent() -> str:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    value = os.getenv("SEC_USER_AGENT", "").strip()
    if not value:
        raise DeskError("SEC_USER_AGENT is missing or empty in the project .env file.")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    first_line = path.read_text(encoding="utf-8").splitlines()
    if not first_line:
        raise DeskError(f"CSV output has no header: {path}")


def safe_folder_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "company"


def print_step(number: int) -> None:
    print(f"\nStep {number}: {STEP_NAMES[number]}")


def normalize_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not ticker:
        raise DeskError("Ticker must not be empty.")
    if not re.fullmatch(r"[A-Z0-9.-]+", ticker):
        raise DeskError(f"Ticker contains unsupported characters: {value!r}")
    return ticker


def resolve_ticker(client: SECClient, ticker: str) -> Company:
    data = client.json(COMPANY_TICKERS_URL)
    matches = []
    for item in data.values():
        if str(item.get("ticker", "")).upper() == ticker.upper():
            matches.append(item)
    if not matches:
        raise DeskError(f"Ticker {ticker} was not found in SEC company_tickers.json.")
    unique_ciks = {int(item["cik_str"]) for item in matches}
    if len(unique_ciks) != 1:
        raise DeskError(f"Ticker {ticker} is ambiguous in SEC company_tickers.json.")
    item = matches[0]
    return Company(ticker=ticker.upper(), name=str(item["title"]), cik=int(item["cik_str"]))


def rows_from_parallel_arrays(source: dict[str, Any], source_name: str) -> list[dict[str, Any]]:
    forms = source.get("form", [])
    rows: list[dict[str, Any]] = []
    for index in range(len(forms)):
        row: dict[str, Any] = {"source_submission_file": source_name}
        for key, values in source.items():
            if isinstance(values, list):
                row[key] = values[index] if index < len(values) else ""
        rows.append(row)
    return rows


def get_all_submission_rows(client: SECClient, company: Company) -> list[dict[str, Any]]:
    url = f"{SEC_DATA}/submissions/CIK{company.cik10}.json"
    data = client.json(url)
    filings = data.get("filings", {})
    rows = rows_from_parallel_arrays(filings.get("recent", {}), "recent")
    for historical in filings.get("files", []):
        name = historical.get("name")
        if not name:
            continue
        historical_data = client.json(f"{SEC_DATA}/submissions/{name}")
        rows.extend(rows_from_parallel_arrays(historical_data, str(name)))
    return rows


def filing_index_url(company: Company, accession: str) -> str:
    return f"{SEC_ARCHIVES}/{company.cik}/{accession.replace('-', '')}/{accession}-index.html"


def filing_archive_base(company: Company, accession: str) -> str:
    return f"{SEC_ARCHIVES}/{company.cik}/{accession.replace('-', '')}"


def parse_accepted_timestamp(index_html: str, url: str) -> str:
    text = BeautifulSoup(index_html, "html.parser").get_text(" ", strip=True)
    patterns = (
        r"Accepted\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
        r"Accepted\s+(\d{8}\d{6})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1)
            if value.isdigit() and len(value) == 14:
                return datetime.strptime(value, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            return value
    raise DeskError(f"Could not verify the Accepted timestamp on EDGAR index page: {url}")


def row_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    accepted = str(row.get("acceptanceDateTime") or "")
    filed = str(row.get("filingDate") or "")
    return accepted, filed


def select_filings(client: SECClient, company: Company) -> dict[str, dict[str, Any]]:
    rows = get_all_submission_rows(client, company)
    requirements = {
        "10-k": lambda row: row.get("form") == "10-K",
        "10-q": lambda row: row.get("form") == "10-Q",
        "8-k": lambda row: row.get("form") == "8-K"
        and "2.02" in {item.strip() for item in str(row.get("items", "")).split(",")},
    }
    selected: dict[str, dict[str, Any]] = {}
    for key, predicate in requirements.items():
        candidates = [row for row in rows if predicate(row)]
        if not candidates:
            label = "8-K reporting Item 2.02" if key == "8-k" else key.upper()
            raise DeskError(f"No required {label} filing was found for {company.ticker}.")
        row = dict(max(candidates, key=row_sort_key))
        accession = str(row.get("accessionNumber", ""))
        if not accession:
            raise DeskError(f"Selected {key.upper()} filing has no accession number.")
        index_url = filing_index_url(company, accession)
        accepted_on_index = parse_accepted_timestamp(client.text(index_url), index_url)
        row.update(
            {
                "accepted_on_index": accepted_on_index,
                "index_url": index_url,
                "archive_base_url": filing_archive_base(company, accession),
            }
        )
        selected[key] = row
    return selected


def print_filing(label: str, filing: dict[str, Any]) -> None:
    print(
        f"{label}: form={filing.get('form')} | filed={filing.get('filingDate')} | "
        f"period={filing.get('reportDate')} | accession={filing.get('accessionNumber')} | "
        f"primary={filing.get('primaryDocument')} | accepted={filing.get('accepted_on_index')}"
    )
    print(f"  {filing.get('index_url')}")


def parse_filing_documents(index_html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(index_html, "html.parser")
    documents: list[dict[str, str]] = []
    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True).lower() for cell in table.find_all("th")]
        if "document" not in headers or "type" not in headers:
            continue
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            link = cells[2].find("a", href=True)
            if not link:
                continue
            href = str(link["href"])
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"{SEC_WWW}{href}"
            else:
                url = f"{base_url}/{href}"
            documents.append(
                {
                    "sequence": cells[0].get_text(" ", strip=True),
                    "description": cells[1].get_text(" ", strip=True),
                    "document": link.get_text(" ", strip=True),
                    "url": url,
                    "type": cells[3].get_text(" ", strip=True).upper(),
                }
            )
    return documents


def select_exhibit_99_1(documents: list[dict[str, str]]) -> dict[str, str]:
    candidates = [doc for doc in documents if doc.get("type") == "EX-99.1"]
    if not candidates:
        raise DeskError("The selected earnings 8-K has no document with type EX-99.1.")
    keywords = ("earnings", "results", "release", "press")

    def score(doc: dict[str, str]) -> int:
        text = f"{doc.get('description', '')} {doc.get('document', '')}".lower()
        return sum(1 for keyword in keywords if keyword in text)

    highest = max(score(doc) for doc in candidates)
    best = [doc for doc in candidates if score(doc) == highest]
    if len(best) != 1:
        descriptions = "; ".join(f"{doc['document']} ({doc['description']})" for doc in best)
        raise DeskError(f"Several EX-99.1 exhibits are equally valid: {descriptions}")
    return best[0]


def html_to_plain_text(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav"]):
        tag.decompose()
    for row in list(soup.find_all("tr")):
        cells = [re.sub(r"\s+", " ", cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if cells:
            row.replace_with(NavigableString("\n" + " | ".join(cells) + "\n"))
    lines = []
    for line in soup.get_text("\n").splitlines():
        cleaned = re.sub(r"[ \t\xa0]+", " ", line).strip()
        if cleaned and (not lines or cleaned != lines[-1]):
            lines.append(cleaned)
    return "\n".join(lines) + "\n"


def response_to_plain_text(response: requests.Response) -> str:
    content_type = response.headers.get("Content-Type", "").lower()
    raw = response.text
    if "html" in content_type or re.search(r"<\s*(html|body|table|div)\b", raw[:5000], re.I):
        return html_to_plain_text(raw)
    return "\n".join(line.rstrip() for line in raw.splitlines() if line.strip()) + "\n"


def download_documents(
    client: SECClient, company: Company, filings: dict[str, dict[str, Any]], run_folder: Path
) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    mapping = {"10-k": "10-k.txt", "10-q": "10-q.txt", "8-k": "8-k.txt"}
    for key, filename in mapping.items():
        filing = filings[key]
        primary = str(filing.get("primaryDocument", ""))
        if not primary:
            raise DeskError(f"The selected {key.upper()} has no primary document.")
        url = f"{filing['archive_base_url']}/{primary}"
        response = client.get(url)
        text = response_to_plain_text(response)
        if len(text.strip()) < 100:
            raise DeskError(f"Downloaded {key.upper()} document has no usable text: {url}")
        path = run_folder / filename
        path.write_text(text, encoding="utf-8")
        outputs[key] = {
            "source_url": url,
            "local_filename": filename,
            "accession_number": filing["accessionNumber"],
            "retrieval_status": "success",
        }

    earnings_filing = filings["8-k"]
    index_html = client.text(str(earnings_filing["index_url"]))
    documents = parse_filing_documents(index_html, str(earnings_filing["archive_base_url"]))
    exhibit = select_exhibit_99_1(documents)
    response = client.get(exhibit["url"])
    text = response_to_plain_text(response)
    if len(text.strip()) < 100:
        raise DeskError(f"Downloaded Exhibit 99.1 has no usable text: {exhibit['url']}")
    filename = "exhibit-99-1.txt"
    (run_folder / filename).write_text(text, encoding="utf-8")
    outputs["exhibit-99-1"] = {
        "source_url": exhibit["url"],
        "local_filename": filename,
        "accession_number": earnings_filing["accessionNumber"],
        "document_type": exhibit["type"],
        "description": exhibit["description"],
        "retrieval_status": "success",
    }
    return outputs


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def valid_observations(
    facts_data: dict[str, Any], tag: str, spec: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    fact = facts_data.get("facts", {}).get("us-gaap", {}).get(tag)
    if not fact:
        return [], ["tag absent from us-gaap company facts"]
    unit_key = next((key for key in spec["unit_keys"] if key in fact.get("units", {})), None)
    if not unit_key:
        return [], [f"compatible units absent; expected one of {spec['unit_keys']}"]
    accepted: list[dict[str, Any]] = []
    for observation in fact["units"][unit_key]:
        if observation.get("form") != "10-K":
            continue
        if observation.get("fp") != "FY":
            continue
        end = parse_iso_date(str(observation.get("end", "")))
        if not end:
            continue
        item = dict(observation)
        item["source_unit_key"] = unit_key
        if spec["kind"] == "duration":
            start = parse_iso_date(str(observation.get("start", "")))
            if not start:
                continue
            days = (end - start).days + 1
            if days < 300 or days > 400:
                continue
            item["duration_days"] = days
        accepted.append(item)
    if not accepted:
        return [], ["no valid annual 10-K observations with a compatible unit"]
    return accepted, []


def dedupe_observations(observations: Iterable[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    selected: dict[tuple[str, ...], dict[str, Any]] = {}
    for observation in observations:
        key = (
            (str(observation.get("start", "")), str(observation.get("end", "")))
            if kind == "duration"
            else (str(observation.get("end", "")),)
        )
        prior = selected.get(key)
        rank = (str(observation.get("filed", "")), str(observation.get("accn", "")))
        prior_rank = (str(prior.get("filed", "")), str(prior.get("accn", ""))) if prior else ("", "")
        if prior is None or rank > prior_rank:
            selected[key] = observation
    return list(selected.values())


def observation_source_url(company: Company, observation: dict[str, Any]) -> str:
    accession = str(observation.get("accn", ""))
    if not accession:
        return f"{SEC_DATA}/api/xbrl/companyfacts/CIK{company.cik10}.json"
    return filing_index_url(company, accession)


def format_observation(
    company: Company, tag: str, spec: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    return {
        "value": observation.get("val"),
        "unit": spec["unit"],
        "source_unit_key": observation.get("source_unit_key"),
        # SEC's `fy` can be the reporting filing's year for comparative facts.
        # Label each fact by the year in its own period end instead.
        "fiscal_year": int(str(observation.get("end", ""))[:4]) if str(observation.get("end", ""))[:4].isdigit() else observation.get("fy"),
        "fiscal_period": observation.get("fp"),
        "period_start": observation.get("start"),
        "period_end": observation.get("end"),
        "filing_form": observation.get("form"),
        "filing_date": observation.get("filed"),
        "accession_number": observation.get("accn"),
        "frame": observation.get("frame"),
        "xbrl_tag": f"us-gaap:{tag}",
        "source_url": observation_source_url(company, observation),
    }


def select_revenue_reference(
    company: Company, facts_data: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    spec = CONCEPTS["total_revenue"]
    candidates = []
    rejected: dict[str, str] = {}
    for priority, tag in enumerate(spec["tags"]):
        observations, reasons = valid_observations(facts_data, tag, spec)
        observations = dedupe_observations(observations, "duration")
        observations.sort(key=lambda item: (str(item.get("end", "")), str(item.get("start", ""))))
        if not observations:
            rejected[tag] = "; ".join(reasons)
            continue
        candidates.append(
            {
                "tag": tag,
                "priority": priority,
                "observations": observations,
                "latest_end": str(observations[-1]["end"]),
                "has_current_and_prior": len(observations) >= 2,
            }
        )
    if not candidates:
        raise DeskError(f"No valid annual total-revenue XBRL fact was found for {company.ticker}.")
    if any(candidate["has_current_and_prior"] for candidate in candidates):
        eligible = [candidate for candidate in candidates if candidate["has_current_and_prior"]]
    else:
        eligible = candidates
    chosen = sorted(eligible, key=lambda item: (item["latest_end"], -item["priority"]), reverse=True)[0]
    observations = chosen["observations"]
    current = observations[-1]
    prior = observations[-2] if len(observations) >= 2 else None
    for candidate in candidates:
        if candidate["tag"] != chosen["tag"]:
            rejected[candidate["tag"]] = (
                f"not selected; latest valid annual end {candidate['latest_end']}; "
                f"current-and-prior coverage={candidate['has_current_and_prior']}"
            )
    result = {
        "concept": "total_revenue",
        "label": spec["label"],
        "status": "available",
        "selected_tag": f"us-gaap:{chosen['tag']}",
        "selection_reason": (
            "Selected the highest-priority candidate among tags with current-and-prior annual coverage "
            f"whose latest valid 10-K fiscal-year end is {current['end']}."
        ),
        "current": format_observation(company, chosen["tag"], spec, current),
        "prior": format_observation(company, chosen["tag"], spec, prior) if prior else None,
        "rejected_candidate_tags": rejected,
    }
    return result, rejected


def match_reference_period(
    observation: dict[str, Any], kind: str, reference: dict[str, Any]
) -> bool:
    if str(observation.get("end")) != str(reference.get("end")):
        return False
    if kind == "duration" and str(observation.get("start")) != str(reference.get("start")):
        return False
    return True


def select_aligned_concept(
    company: Company,
    facts_data: dict[str, Any],
    key: str,
    current_reference: dict[str, Any],
    prior_reference: dict[str, Any] | None,
) -> dict[str, Any]:
    spec = CONCEPTS[key]
    candidates = []
    rejected: dict[str, str] = {}
    for priority, tag in enumerate(spec["tags"]):
        observations, reasons = valid_observations(facts_data, tag, spec)
        observations = dedupe_observations(observations, spec["kind"])
        current_matches = [
            observation
            for observation in observations
            if match_reference_period(observation, spec["kind"], current_reference)
        ]
        prior_matches = (
            [
                observation
                for observation in observations
                if match_reference_period(observation, spec["kind"], prior_reference)
            ]
            if prior_reference
            else []
        )
        if not current_matches:
            rejected[tag] = (
                "; ".join(reasons)
                if reasons
                else f"no observation aligned to reference period ending {current_reference['end']}"
            )
            continue
        candidates.append(
            {
                "tag": tag,
                "priority": priority,
                "current": max(current_matches, key=lambda item: (str(item.get("filed", "")), str(item.get("accn", "")))),
                "prior": (
                    max(prior_matches, key=lambda item: (str(item.get("filed", "")), str(item.get("accn", ""))))
                    if prior_matches
                    else None
                ),
            }
        )
    if not candidates:
        return {
            "concept": key,
            "label": spec["label"],
            "status": "unavailable",
            "reason": f"No candidate tag aligns to the reference fiscal year ending {current_reference['end']}.",
            "selected_tag": None,
            "selection_reason": None,
            "current": None,
            "prior": None,
            "rejected_candidate_tags": rejected,
        }
    with_prior = [candidate for candidate in candidates if candidate["prior"] is not None]
    chosen = min(with_prior or candidates, key=lambda item: item["priority"])
    for candidate in candidates:
        if candidate["tag"] != chosen["tag"]:
            rejected[candidate["tag"]] = (
                "not selected; a higher-priority aligned candidate had equivalent or better period coverage"
            )
    return {
        "concept": key,
        "label": spec["label"],
        "status": "available",
        "selected_tag": f"us-gaap:{chosen['tag']}",
        "selection_reason": (
            "Selected the highest-priority candidate aligned to the revenue reference period"
            + (" with prior-period coverage." if chosen["prior"] else "; prior-period coverage was unavailable.")
        ),
        "current": format_observation(company, chosen["tag"], spec, chosen["current"]),
        "prior": (
            format_observation(company, chosen["tag"], spec, chosen["prior"])
            if chosen["prior"]
            else None
        ),
        "rejected_candidate_tags": rejected,
    }


def retrieve_company_facts(client: SECClient, company: Company) -> dict[str, Any]:
    source_url = f"{SEC_DATA}/api/xbrl/companyfacts/CIK{company.cik10}.json"
    facts_data = client.json(source_url)
    revenue, _ = select_revenue_reference(company, facts_data)
    revenue_current = revenue["current"]
    revenue_prior = revenue["prior"]
    if not revenue_prior:
        raise DeskError(f"No prior annual total-revenue period was found for {company.ticker}.")
    current_reference = {
        "start": revenue_current["period_start"],
        "end": revenue_current["period_end"],
    }
    prior_reference = {
        "start": revenue_prior["period_start"],
        "end": revenue_prior["period_end"],
    }
    concepts: OrderedDict[str, dict[str, Any]] = OrderedDict()
    concepts["total_revenue"] = revenue
    for key in list(CONCEPTS.keys())[1:]:
        concepts[key] = select_aligned_concept(
            company, facts_data, key, current_reference, prior_reference
        )
    return {
        "company": company.as_dict(),
        "company_facts_source_url": source_url,
        "reference_fiscal_year": {
            "fiscal_year": revenue_current["fiscal_year"],
            "period_start": revenue_current["period_start"],
            "period_end": revenue_current["period_end"],
            "selected_revenue_tag": revenue["selected_tag"],
        },
        "prior_fiscal_year": {
            "fiscal_year": revenue_prior["fiscal_year"],
            "period_start": revenue_prior["period_start"],
            "period_end": revenue_prior["period_end"],
        },
        "concepts": concepts,
    }


def facts_csv_rows(facts: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, concept in facts["concepts"].items():
        for period_label in ("current", "prior"):
            observation = concept.get(period_label)
            rows.append(
                {
                    "concept": key,
                    "label": concept["label"],
                    "status": concept["status"],
                    "period_label": period_label,
                    "value": observation.get("value") if observation else "",
                    "unit": observation.get("unit") if observation else "",
                    "fiscal_year": observation.get("fiscal_year") if observation else "",
                    "period_start": observation.get("period_start") if observation else "",
                    "period_end": observation.get("period_end") if observation else "",
                    "selected_tag": concept.get("selected_tag") or "",
                    "filing_form": observation.get("filing_form") if observation else "",
                    "filing_date": observation.get("filing_date") if observation else "",
                    "accession_number": observation.get("accession_number") if observation else "",
                    "source_url": observation.get("source_url") if observation else "",
                }
            )
    return rows


FACT_CSV_FIELDS = [
    "concept",
    "label",
    "status",
    "period_label",
    "value",
    "unit",
    "fiscal_year",
    "period_start",
    "period_end",
    "selected_tag",
    "filing_form",
    "filing_date",
    "accession_number",
    "source_url",
]


def print_facts(facts: dict[str, Any]) -> None:
    reference = facts["reference_fiscal_year"]
    print(
        f"Reference fiscal year: FY{reference['fiscal_year']} | "
        f"{reference['period_start']} to {reference['period_end']}"
    )
    for concept in facts["concepts"].values():
        current = concept.get("current")
        prior = concept.get("prior")
        if not current:
            print(f"{concept['label']}: unavailable | {concept.get('reason')}")
            continue
        prior_text = (
            f"; prior={prior['value']} {prior['unit']} ({prior['period_end']})" if prior else "; prior unavailable"
        )
        print(
            f"{concept['label']}: {current['value']} {current['unit']} | "
            f"{current['xbrl_tag']} | period end {current['period_end']} | "
            f"{current['filing_form']} {current['accession_number']}{prior_text}"
        )


def value_at(facts: dict[str, Any], concept: str, period: str = "current") -> Any | None:
    observation = facts["concepts"].get(concept, {}).get(period)
    return observation.get("value") if observation else None


def period_at(facts: dict[str, Any], concept: str, period: str = "current") -> str | None:
    observation = facts["concepts"].get(concept, {}).get(period)
    return observation.get("period_end") if observation else None


def calculation(
    name: str,
    formula: str,
    inputs: dict[str, Any],
    periods: dict[str, Any],
    unit: str,
    arithmetic: str,
    result: Any | None,
    reason: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "measure": name,
        "formula": formula,
        "inputs": inputs,
        "fiscal_periods": periods,
        "unit": unit,
        "arithmetic": arithmetic,
        "result": result,
        "validation_status": "available" if reason is None else "unavailable",
        "unavailable_reason": reason,
        "note": note,
    }


def calculate_measures(facts: dict[str, Any], price: float | None) -> dict[str, Any]:
    results: OrderedDict[str, dict[str, Any]] = OrderedDict()

    revenue = value_at(facts, "total_revenue")
    prior_revenue = value_at(facts, "total_revenue", "prior")
    if revenue is not None and prior_revenue not in (None, 0):
        result = (revenue - prior_revenue) / prior_revenue
        results["revenue_growth"] = calculation(
            "Revenue growth",
            "(Current-year revenue - Prior-year revenue) / Prior-year revenue",
            {"current_revenue": revenue, "prior_revenue": prior_revenue},
            {"current": period_at(facts, "total_revenue"), "prior": period_at(facts, "total_revenue", "prior")},
            "ratio",
            f"({revenue} - {prior_revenue}) / {prior_revenue}",
            result,
        )
    else:
        results["revenue_growth"] = calculation(
            "Revenue growth", "(Current-year revenue - Prior-year revenue) / Prior-year revenue", {}, {}, "ratio", "", None,
            "Revenue input is missing or prior revenue is zero.",
        )

    operating_income = value_at(facts, "operating_income")
    if operating_income is not None and revenue not in (None, 0):
        result = operating_income / revenue
        results["operating_margin"] = calculation(
            "Operating margin", "Current-year operating income / Current-year total revenue",
            {"operating_income": operating_income, "total_revenue": revenue},
            {"period_end": period_at(facts, "total_revenue")}, "ratio",
            f"{operating_income} / {revenue}", result,
            note="Denominator is total revenue, not net sales.",
        )
    else:
        results["operating_margin"] = calculation(
            "Operating margin", "Current-year operating income / Current-year total revenue", {}, {}, "ratio", "", None,
            "Operating income or total revenue is missing, or total revenue is zero.",
        )

    net_income = value_at(facts, "net_income")
    equity = value_at(facts, "stockholders_equity")
    prior_equity = value_at(facts, "stockholders_equity", "prior")
    average_equity = ((equity + prior_equity) / 2) if equity is not None and prior_equity is not None else None
    if net_income is not None and average_equity not in (None, 0):
        result = net_income / average_equity
        results["return_on_average_equity"] = calculation(
            "Return on average equity", "Current-year net income / average current-and-prior equity",
            {"net_income": net_income, "current_equity": equity, "prior_equity": prior_equity},
            {"current": period_at(facts, "stockholders_equity"), "prior": period_at(facts, "stockholders_equity", "prior")},
            "ratio", f"{net_income} / (({equity} + {prior_equity}) / 2)", result,
        )
    else:
        results["return_on_average_equity"] = calculation(
            "Return on average equity", "Current-year net income / average current-and-prior equity", {}, {}, "ratio", "", None,
            "Net income or current/prior equity is missing, or average equity is zero.",
        )

    debt = value_at(facts, "long_term_debt")
    current_debt = value_at(facts, "current_long_term_debt")
    if debt is not None and current_debt is not None and equity not in (None, 0):
        result = (debt + current_debt) / equity
        results["debt_to_equity"] = calculation(
            "Debt to equity", "(Long-term debt + Current portion of long-term debt) / Stockholders' equity",
            {"long_term_debt": debt, "current_portion": current_debt, "stockholders_equity": equity},
            {"period_end": period_at(facts, "stockholders_equity")}, "ratio",
            f"({debt} + {current_debt}) / {equity}", result,
        )
    else:
        results["debt_to_equity"] = calculation(
            "Debt to equity", "(Long-term debt + Current portion of long-term debt) / Stockholders' equity", {}, {}, "ratio", "", None,
            "Long-term debt, its current portion, or equity is missing, or equity is zero. Missing debt is not treated as zero.",
        )

    cash_from_operations = value_at(facts, "cash_from_operations")
    additions = value_at(facts, "property_equipment_additions")
    if cash_from_operations is not None and additions is not None:
        result = cash_from_operations - abs(additions)
        results["free_cash_flow"] = calculation(
            "Free cash flow", "Net cash from operations - Additions to property and equipment",
            {"cash_from_operations": cash_from_operations, "property_equipment_additions_sec_value": additions, "property_equipment_additions_as_positive_expenditure": abs(additions)},
            {"period_end": period_at(facts, "cash_from_operations")}, "USD",
            f"{cash_from_operations} - {abs(additions)}", result,
            note="The original SEC value is preserved. The calculation treats additions as a positive expenditure amount.",
        )
    else:
        results["free_cash_flow"] = calculation(
            "Free cash flow", "Net cash from operations - Additions to property and equipment", {}, {}, "USD", "", None,
            "Cash from operations or property-and-equipment additions is missing.",
        )

    diluted_eps = value_at(facts, "diluted_eps")
    if price is None:
        reason = "--price was not supplied."
    elif diluted_eps in (None, 0):
        reason = "Diluted EPS is missing or zero."
    else:
        reason = None
    if reason is None:
        result = price / diluted_eps
        note = "Price divided by latest fiscal-year diluted EPS. This is not labeled TTM P/E."
        if diluted_eps < 0:
            note += " The arithmetic result is not economically meaningful because diluted EPS is negative."
        results["price_to_earnings"] = calculation(
            "Price-to-earnings ratio", "User-supplied share price / Latest fiscal-year diluted EPS",
            {"share_price": price, "diluted_eps": diluted_eps},
            {"diluted_eps_period_end": period_at(facts, "diluted_eps")}, "multiple",
            f"{price} / {diluted_eps}", result, note=note,
        )
    else:
        results["price_to_earnings"] = calculation(
            "Price-to-earnings ratio", "User-supplied share price / Latest fiscal-year diluted EPS", {}, {}, "multiple", "", None, reason,
            note="Price divided by latest fiscal-year diluted EPS. This is not TTM P/E.",
        )

    return {"definition": "All ratios use the stated filing periods and total-revenue definition.", "calculations": results}


def print_calculations(data: dict[str, Any]) -> None:
    for item in data["calculations"].values():
        if item["validation_status"] == "available":
            print(f"{item['measure']}: {item['arithmetic']} = {item['result']} {item['unit']}")
        else:
            print(f"{item['measure']}: unavailable | {item['unavailable_reason']}")


def source_candidates(lines: list[str], kind: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    income_statement_lines = [
        index for index, text in enumerate(lines)
        if re.search(r"statements? of (income|operations|earnings)", text, flags=re.IGNORECASE)
    ]
    operations_statement_lines = [
        index for index, text in enumerate(lines)
        if re.search(r"statements? of operations", text, flags=re.IGNORECASE)
    ]
    for index, line in enumerate(lines):
        lower = line.lower()
        has_number = bool(re.search(r"\d", line))
        if kind == "total_revenue":
            is_income_statement_row = bool(re.match(r"^\s*(?:total\s+)?revenues?\s*\|", line, flags=re.IGNORECASE))
            nearest_statement_heading = max((heading for heading in income_statement_lines if heading < index), default=None)
            is_near_statement_heading = nearest_statement_heading is not None and index - nearest_statement_heading <= 40
            is_constant_currency = "(cc)" in lower or "constant currency" in lower
            # Some releases state quarterly revenue in prose rather than a
            # "Total revenue" table row. Preserve that exact source line too.
            matches = bool(re.search(r"\b(?:total\s+)?(?:quarterly\s+)?revenues?\b", lower)) and has_number and not is_constant_currency
            score = 10 if matches and is_income_statement_row and is_near_statement_heading else (4 if matches else 0)
            if matches and is_income_statement_row:
                score += 2
            if matches and re.search(r"\bcompany posted quarterly revenue of\b", lower):
                score += 4
        else:
            excluded = any(word in lower for word in ("share used", "shares used", "weighted average", "diluted shares"))
            matches = "diluted" in lower and has_number and not excluded
            score = 2 if matches else 0
            if matches and any(word in lower for word in ("earnings", "income per", "net income")):
                score += 2
            if matches and ("$" in line or re.search(r"\d+\.\d{2}", line)):
                score += 1
            # Prefer an explicitly GAAP diluted-EPS line over an adjusted-EPS
            # reconciliation row. This prevents non-GAAP EPS from winning
            # merely because it appears earlier or uses a more obvious label.
            if matches and re.search(r"\bgaap\b", lower):
                score += 4
            if matches and re.search(r"gaap\s+income\s*\(loss\)\s+per\s+diluted\s+share", lower):
                score += 2
            if matches and "adjusted" in lower:
                score -= 4
            nearest_operations_statement = max(
                (heading for heading in operations_statement_lines if heading < index),
                default=None,
            )
            preceding_context = " ".join(lines[max(0, index - 3):index]).lower()
            is_diluted_statement_row = bool(re.match(r"^\s*diluted\s*\|", line, flags=re.IGNORECASE))
            if (
                matches
                and is_diluted_statement_row
                and nearest_operations_statement is not None
                and index - nearest_operations_statement <= 40
                and re.search(r"earnings per share", preceding_context)
            ):
                # Prefer the labeled GAAP diluted row in the consolidated
                # statement over repeated summary or prose mentions.
                score += 5
        if matches:
            candidates.append({"line_start": index + 1, "line_end": index + 1, "text": line, "score": score})
    candidates.sort(key=lambda item: (-item["score"], item["line_start"]))
    return candidates[:10]


def extract_release_claims(run_folder: Path) -> dict[str, Any]:
    filename = "exhibit-99-1.txt"
    path = run_folder / filename
    if not path.exists():
        raise DeskError(f"Step 6 requires {filename} from Step 3.")
    lines = path.read_text(encoding="utf-8").splitlines()
    output: dict[str, Any] = {"source_filename": filename, "claims": {}}
    for kind, label in (("total_revenue", "Quarterly total revenue"), ("diluted_eps", "Quarterly diluted EPS")):
        candidates = source_candidates(lines, kind)
        if not candidates:
            output["claims"][kind] = {
                "label": label,
                "status": "not_found",
                "reason": "No exact source line matching the conservative search rule was found.",
                "candidates": [],
            }
            print(f"{label}: not found in {filename}.")
            continue
        top_score = candidates[0]["score"]
        top = [candidate for candidate in candidates if candidate["score"] == top_score]
        status = "candidate_ambiguity" if len(top) > 1 else "found"
        output["claims"][kind] = {
            "label": label,
            "status": status,
            "quoted_source_text": top[0]["text"] if len(top) == 1 else None,
            "source_line_start": top[0]["line_start"] if len(top) == 1 else None,
            "source_line_end": top[0]["line_end"] if len(top) == 1 else None,
            "candidates": top,
            "note": "Quoted source text; no value was calculated, inferred, or paraphrased.",
        }
        if len(top) == 1:
            print(f"{label} — quoted source text ({filename}:{top[0]['line_start']}):")
            print(top[0]["text"])
        else:
            print(f"{label}: several source lines are equally plausible; candidates follow.")
            for candidate in top:
                print(f"  {filename}:{candidate['line_start']}: {candidate['text']}")
    return output


def peer_rows(peer_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for peer in peer_results:
        if peer.get("status") != "success":
            rows.append({"ticker": peer.get("ticker"), "status": "failed", "error": peer.get("error")})
            continue
        company = peer["company"]
        margin = peer["operating_margin"]
        for key, concept in peer["facts"]["concepts"].items():
            current = concept.get("current")
            rows.append(
                {
                    "ticker": company["ticker"],
                    "legal_name": company["legal_name"],
                    "cik": company["cik"],
                    "status": concept["status"],
                    "concept": key,
                    "value": current.get("value") if current else "",
                    "unit": current.get("unit") if current else "",
                    "fiscal_year": current.get("fiscal_year") if current else "",
                    "period_end": current.get("period_end") if current else "",
                    "selected_tag": concept.get("selected_tag") or "",
                    "filing_form": current.get("filing_form") if current else "",
                    "filing_date": current.get("filing_date") if current else "",
                    "accession_number": current.get("accession_number") if current else "",
                    "operating_margin": margin.get("result"),
                    "operating_margin_status": margin.get("validation_status"),
                    "error": "",
                }
            )
    return rows


PEER_CSV_FIELDS = [
    "ticker", "legal_name", "cik", "status", "concept", "value", "unit", "fiscal_year",
    "period_end", "selected_tag", "filing_form", "filing_date", "accession_number",
    "operating_margin", "operating_margin_status", "error",
]


def process_peers(client: SECClient, peer_tickers: list[str]) -> dict[str, Any]:
    results = []
    for ticker in peer_tickers:
        print(f"Peer {ticker}:")
        try:
            company = resolve_ticker(client, ticker)
            facts = retrieve_company_facts(client, company)
            calculations = calculate_measures(facts, price=None)
            margin = calculations["calculations"]["operating_margin"]
            revenue = facts["concepts"]["total_revenue"]["current"]
            operating_income = facts["concepts"]["operating_income"].get("current")
            print(
                f"  {company.name} | FY end {revenue['period_end']} | revenue={revenue['value']} {revenue['unit']} "
                f"({facts['concepts']['total_revenue']['selected_tag']})"
            )
            if operating_income:
                print(f"  operating income={operating_income['value']} {operating_income['unit']}")
            print(f"  operating margin={margin.get('result')} | status={margin['validation_status']}")
            results.append(
                {
                    "ticker": ticker,
                    "status": "success",
                    "company": company.as_dict(),
                    "facts": facts,
                    "operating_margin": margin,
                }
            )
        except Exception as exc:  # Continue with remaining peers as required.
            message = f"{type(exc).__name__}: {exc}"
            print(f"  failed: {message}")
            results.append({"ticker": ticker, "status": "failed", "error": message})
    return {"definition": "Operating income divided by total revenue for each peer's own latest fiscal year.", "peers": results}


def new_manifest(company: Company, args: argparse.Namespace, now: datetime) -> dict[str, Any]:
    return {
        "program_version": PROGRAM_VERSION,
        "run_status": "running",
        "steps": {str(number): {"name": STEP_NAMES[number], "status": "not_run"} for number in STEP_NAMES},
        "local_run_time": now.isoformat(),
        "utc_run_time": now.astimezone(timezone.utc).isoformat(),
        "time_zone": str(now.tzinfo),
        "arguments": {
            "ticker": args.ticker,
            "peers": args.peers,
            "price": args.price,
            "price_date": args.price_date,
            "price_source": args.price_source,
            "step": args.step,
        },
        "main_ticker": company.ticker,
        "peer_tickers": parse_peers(args.peers),
        "company": company.as_dict(),
        "source_urls": {"company_tickers": COMPANY_TICKERS_URL},
        "filings": {},
        "selected_xbrl_tags": {},
        "output_filenames": ["manifest.json"],
        "retrieval_errors": [],
        "validation_errors": [],
        "unavailable_values": [],
    }


def mark_step(manifest: dict[str, Any], number: int, status: str, **extra: Any) -> None:
    manifest["steps"][str(number)] = {"name": STEP_NAMES[number], "status": status, **extra}


def save_manifest(run_folder: Path, manifest: dict[str, Any]) -> None:
    write_json(run_folder / "manifest.json", manifest)


def create_run_folder(company: Company, now: datetime) -> Path:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    name = f"{safe_folder_component(company.name)}_{company.ticker}_{now.strftime('%Y%m%d_%H%M%S')}"
    folder = RUNS_ROOT / name
    folder.mkdir(parents=False, exist_ok=False)
    return folder


def parse_peers(value: str | None) -> list[str]:
    if not value:
        return []
    peers = []
    for raw in value.split(","):
        ticker = normalize_ticker(raw)
        if ticker not in peers:
            peers.append(ticker)
    return peers


def company_from_manifest(manifest: dict[str, Any]) -> Company:
    data = manifest["company"]
    return Company(ticker=data["ticker"], name=data["legal_name"], cik=int(data["cik"]))


def newest_run_folder(ticker: str) -> Path:
    if not RUNS_ROOT.exists():
        raise DeskError(f"No saved runs exist for single-step execution of {ticker}.")
    candidates = []
    for path in RUNS_ROOT.iterdir():
        manifest_path = path / "manifest.json"
        if not path.is_dir() or not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(manifest.get("main_ticker", "")).upper() == ticker:
            candidates.append((str(manifest.get("local_run_time", "")), path))
    if not candidates:
        raise DeskError(f"No saved run folder exists for {ticker}.")
    return max(candidates, key=lambda item: item[0])[1]


def require_file(run_folder: Path, filename: str, step: int) -> Path:
    path = run_folder / filename
    if not path.exists():
        raise DeskError(f"Step {step} requires {filename}, but it is unavailable in {run_folder}.")
    return path


def execute_step(
    number: int,
    client: SECClient,
    company: Company,
    args: argparse.Namespace,
    run_folder: Path,
    manifest: dict[str, Any],
) -> None:
    print_step(number)
    mark_step(manifest, number, "running")
    save_manifest(run_folder, manifest)
    try:
        if number == 1:
            print(f"Ticker: {company.ticker} | Company: {company.name} | CIK: {company.cik} ({company.cik10})")
            manifest["source_urls"]["company_tickers"] = COMPANY_TICKERS_URL
            mark_step(manifest, 1, "success")

        elif number == 2:
            filings = select_filings(client, company)
            for label, filing in filings.items():
                print_filing(label.upper(), filing)
            write_json(run_folder / "filings.json", filings)
            manifest["filings"] = {
                key: {
                    "form": item.get("form"), "filing_date": item.get("filingDate"),
                    "reporting_period": item.get("reportDate"), "accession_number": item.get("accessionNumber"),
                    "accepted_timestamp": item.get("accepted_on_index"), "index_url": item.get("index_url"),
                }
                for key, item in filings.items()
            }
            manifest["source_urls"]["submissions"] = f"{SEC_DATA}/submissions/CIK{company.cik10}.json"
            manifest["output_filenames"] = sorted(set(manifest["output_filenames"] + ["filings.json"]))
            mark_step(manifest, 2, "success")

        elif number == 3:
            filings_path = require_file(run_folder, "filings.json", 3)
            filings = json.loads(filings_path.read_text(encoding="utf-8"))
            documents = download_documents(client, company, filings, run_folder)
            manifest["documents"] = documents
            filenames = [item["local_filename"] for item in documents.values()]
            manifest["output_filenames"] = sorted(set(manifest["output_filenames"] + filenames))
            for key, item in documents.items():
                print(f"{key}: saved {item['local_filename']} from {item['source_url']}")
            mark_step(manifest, 3, "success")

        elif number == 4:
            facts = retrieve_company_facts(client, company)
            write_json(run_folder / "facts.json", facts)
            write_csv(run_folder / "facts.csv", facts_csv_rows(facts), FACT_CSV_FIELDS)
            print_facts(facts)
            manifest["source_urls"]["company_facts"] = facts["company_facts_source_url"]
            manifest["selected_xbrl_tags"] = {
                key: concept.get("selected_tag") for key, concept in facts["concepts"].items()
            }
            manifest["tag_selection_reasons"] = {
                key: concept.get("selection_reason") for key, concept in facts["concepts"].items()
            }
            manifest["unavailable_values"] = [
                key for key, concept in facts["concepts"].items() if concept["status"] != "available"
            ]
            manifest["output_filenames"] = sorted(set(manifest["output_filenames"] + ["facts.json", "facts.csv"]))
            mark_step(manifest, 4, "success")

        elif number == 5:
            facts_path = require_file(run_folder, "facts.json", 5)
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
            calculations = calculate_measures(facts, args.price)
            write_json(run_folder / "calculations.json", calculations)
            print_calculations(calculations)
            manifest["arguments"]["price"] = args.price
            manifest["arguments"]["price_date"] = args.price_date
            manifest["arguments"]["price_source"] = args.price_source
            manifest["output_filenames"] = sorted(set(manifest["output_filenames"] + ["calculations.json"]))
            unavailable = [
                key for key, item in calculations["calculations"].items() if item["validation_status"] != "available"
            ]
            manifest["unavailable_values"] = sorted(set(manifest["unavailable_values"] + unavailable))
            mark_step(manifest, 5, "success", unavailable_calculations=unavailable)

        elif number == 6:
            release = extract_release_claims(run_folder)
            facts_path = require_file(run_folder, "facts.json", 6)
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
            facts["earnings_release_extraction"] = release
            write_json(facts_path, facts)
            statuses = {key: item["status"] for key, item in release["claims"].items()}
            mark_step(manifest, 6, "success", extraction_statuses=statuses)

        elif number == 7:
            peers = parse_peers(args.peers) or list(manifest.get("peer_tickers", []))
            peer_data = process_peers(client, peers)
            write_json(run_folder / "peers.json", peer_data)
            write_csv(run_folder / "peers.csv", peer_rows(peer_data["peers"]), PEER_CSV_FIELDS)
            manifest["peer_tickers"] = peers
            manifest["output_filenames"] = sorted(set(manifest["output_filenames"] + ["peers.json", "peers.csv"]))
            failures = [peer for peer in peer_data["peers"] if peer["status"] != "success"]
            if failures:
                manifest["retrieval_errors"].extend(failures)
            mark_step(manifest, 7, "success", peer_failures=len(failures))

        else:
            raise DeskError(f"Unsupported step number: {number}")
    except Exception as exc:
        mark_step(manifest, number, "failed", error=f"{type(exc).__name__}: {exc}")
        manifest["run_status"] = "failed"
        manifest["validation_errors"].append(f"Step {number}: {type(exc).__name__}: {exc}")
        save_manifest(run_folder, manifest)
        raise
    save_manifest(run_folder, manifest)


def validate_complete_run(run_folder: Path, manifest: dict[str, Any]) -> list[str]:
    errors = []
    required = [
        "manifest.json", "filings.json", "10-k.txt", "10-q.txt", "8-k.txt", "exhibit-99-1.txt",
        "facts.json", "facts.csv", "calculations.json", "peers.json", "peers.csv",
    ]
    for filename in required:
        path = run_folder / filename
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"Required output is missing or empty: {filename}")
    for filename in ("manifest.json", "filings.json", "facts.json", "calculations.json", "peers.json"):
        path = run_folder / filename
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                errors.append(f"Invalid JSON: {filename}")
    for filename in ("facts.csv", "peers.csv"):
        path = run_folder / filename
        if path.exists() and not path.read_text(encoding="utf-8").splitlines():
            errors.append(f"CSV has no header: {filename}")
    if any(item["status"] != "success" for item in manifest["steps"].values()):
        errors.append("One or more steps did not report success.")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the seven-step SEC data pipeline for an equity-research desk."
    )
    parser.add_argument("ticker", type=normalize_ticker, help="U.S. public-company ticker")
    parser.add_argument("--peers", help="Comma-separated peer tickers")
    parser.add_argument("--price", type=float, help="Positive share price for fiscal-year P/E")
    parser.add_argument("--price-date", help="Date of the supplied closing share price (YYYY-MM-DD)")
    parser.add_argument("--price-source", help="Source URL or label for the supplied closing share price")
    parser.add_argument("--step", type=int, choices=range(1, 8), help="Run one step only")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.price is not None and args.price <= 0:
        parser.error("--price must be greater than zero")
    if args.price_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.price_date):
        parser.error("--price-date must use YYYY-MM-DD")
    try:
        peers = parse_peers(args.peers)
        if args.ticker in peers:
            raise DeskError("The main ticker must not also appear in --peers.")
        client = SECClient(load_sec_user_agent())
        if args.step and args.step != 1:
            run_folder = newest_run_folder(args.ticker)
            manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))
            company = company_from_manifest(manifest)
            if args.peers is None:
                args.peers = ",".join(manifest.get("peer_tickers", [])) or None
            if args.price is None:
                saved_price = manifest.get("arguments", {}).get("price")
                args.price = float(saved_price) if saved_price is not None else None
            if args.price_date is None:
                args.price_date = manifest.get("arguments", {}).get("price_date")
            if args.price_source is None:
                args.price_source = manifest.get("arguments", {}).get("price_source")
            execute_step(args.step, client, company, args, run_folder, manifest)
            print(f"\nSingle step completed. Run folder: {run_folder}")
            return 0

        print_step(1)
        company = resolve_ticker(client, args.ticker)
        now = datetime.now().astimezone()
        run_folder = create_run_folder(company, now)
        manifest = new_manifest(company, args, now)
        print(f"Ticker: {company.ticker} | Company: {company.name} | CIK: {company.cik} ({company.cik10})")
        mark_step(manifest, 1, "success")
        save_manifest(run_folder, manifest)
        if args.step == 1:
            manifest["run_status"] = "partial_success"
            save_manifest(run_folder, manifest)
            print(f"\nSingle step completed. Run folder: {run_folder}")
            return 0

        for number in range(2, 8):
            execute_step(number, client, company, args, run_folder, manifest)
        errors = validate_complete_run(run_folder, manifest)
        manifest["validation_errors"] = errors
        manifest["run_status"] = "success" if not errors else "failed_validation"
        save_manifest(run_folder, manifest)
        if errors:
            raise DeskError("Run validation failed: " + "; ".join(errors))
        print(f"\nAll seven steps completed. Run folder: {run_folder}")
        return 0
    except DeskError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Error: interrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
