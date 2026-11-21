"""Build token-level numeric claims for the saved FDXF worksheet."""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent
WORKSHEET = BASE / "worksheet.md"
TOKEN_PATTERN = re.compile(
    r"\d{10}-\d{2}-\d{6}|\d{4}-\d{2}-\d{2}|(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?(?![A-Za-z])"
)
ACCESSION_PATTERN = re.compile(r"\d{10}-\d{2}-\d{6}")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def value(token: str) -> str:
    return token.replace(",", "").removesuffix("%").lstrip("+")


def filing(
    *,
    token: str,
    unit: str,
    period: str,
    tag: str,
    form: str,
    accession: str,
    section: str,
    saved_line: str,
    source_file: str,
    source_line: int,
) -> dict[str, object]:
    return {
        "kind": "filing_fact",
        "value": value(token),
        "unit": unit,
        "period": period,
        "source": f"{form}, accession {accession}, {section}, saved line {saved_line}",
        "tag": tag,
        "filing": form,
        "accession": accession,
        "section": section,
        "saved_line": saved_line,
        "source_file": source_file,
        "source_line": source_line,
    }


def arithmetic(
    *, token: str, unit: str, period: str, operation: str, inputs: list[str], round_places: int | None = None
) -> dict[str, object]:
    claim: dict[str, object] = {
        "kind": "arithmetic",
        "value": value(token),
        "unit": unit,
        "period": period,
        "source": "Deterministic worksheet calculation from cited inputs",
        "operation": operation,
        "inputs": inputs,
    }
    if round_places is not None:
        claim["round_places"] = round_places
    return claim


def human(*, token: str, unit: str, period: str, key: str) -> dict[str, object]:
    return {
        "kind": "human_rate",
        "value": value(token),
        "unit": unit,
        "period": period,
        "source": "Frozen human worksheet configuration",
        "config_file": "frozen_numeric_config.json",
        "config_key": key,
        "frozen_value": value(token),
    }


def official_price(token: str) -> dict[str, object]:
    return {
        "kind": "official_exchange_price",
        "value": value(token),
        "unit": "USD per share",
        "period": "2026-11-19 regular close",
        "source": "Nasdaq official historical endpoint",
        "instrument": "FDXF",
        "price_date": "2026-11-19",
        "reader_source": "Nasdaq official historical endpoint",
        "reader_file": "official_close_volume_reader.json",
    }


def market_metric(*, token: str, unit: str, period: str, metric: str) -> dict[str, object]:
    return {
        "kind": "market_metric",
        "value": value(token),
        "unit": unit,
        "period": period,
        "source": "Nasdaq official historical endpoint; saved deterministic reader",
        "instrument": "FDXF",
        "metric": metric,
        "reader_source": "Nasdaq official historical endpoint",
        "reader_file": "official_close_volume_reader.json",
    }


INFO = "filings/final_information_statement_000110465926060223.normalized.txt"
COMPLETION = "filings/fdx_completion_8k_primary_000110465926068519.normalized.txt"
ANNUAL = "filings/fdxf_10k_20260531_000162828026053359.normalized.txt"
QUARTERLY = "filings/fdxf_10q_20260930_000162828026068246.normalized.txt"
FORM4 = "evidence/form4_f3_audit.json"


def explicit_claim(line: str, token: str) -> dict[str, object] | None:
    fy = "Fiscal year ended 2026-05-31"
    quarter = "As of or for the four months ended 2026-09-30"

    specs: list[tuple[str, str, dict[str, object]]] = [
        ("Shares distributed by FedEx", "80.1%", filing(token=token, unit="percent", period="Distribution completed 2026-06-01", tag="distribution_percentage", form="Current report", accession="0001104659-26-068519", section="Item 2.01", saved_line="224", source_file=COMPLETION, source_line=224)),
        ("Stake initially retained", "19.9%", filing(token=token, unit="percent", period="Immediately after distribution", tag="retained_percentage", form="Final information statement", accession="0001104659-26-060223", section="The Spin-Off", saved_line="47", source_file=INFO, source_line=47)),
        ("Senior notes issued", "3.7", filing(token=token, unit="USD billions", period="Issued before the spin-off", tag="senior_notes", form="Quarterly report", accession="0001628280-26-068246", section="Note 7", saved_line="1217", source_file=QUARTERLY, source_line=1217)),
        ("Term loan issued", "0.6", filing(token=token, unit="USD billions", period="Issued before the spin-off", tag="term_loan", form="Quarterly report", accession="0001628280-26-068246", section="Note 7", saved_line="1219", source_file=QUARTERLY, source_line=1219)),
        ("Cash paid to FedEx", "4.1", filing(token=token, unit="USD billions", period="Before the 2026-06-01 effective time", tag="cash_dividend_to_parent", form="Current report", accession="0001104659-26-068519", section="Item 8.01", saved_line="245", source_file=COMPLETION, source_line=245)),
        ("ownership reports reviewed", "34", filing(token=token, unit="ownership reports", period="2026-06-01 through 2026-08-30", tag="form4_filings_found", form="Saved SEC ownership-report audit", accession="aggregate", section="FDXF F3 audit", saved_line="242", source_file=FORM4, source_line=242)),
        ("Funded debt fair value", "4.0", filing(token=token, unit="USD billions", period="2026-09-30", tag="debt_fair_value", form="Quarterly report", accession="0001628280-26-068246", section="Note 7", saved_line="1230", source_file=QUARTERLY, source_line=1230)),
        ("Finance-lease liabilities", "255", filing(token=token, unit="USD millions", period="2026-09-30", tag="finance_lease_liabilities", form="Quarterly report", accession="0001628280-26-068246", section="Note 7", saved_line="1203", source_file=QUARTERLY, source_line=1203)),
        ("Cash:", "388", filing(token=token, unit="USD millions", period="2026-09-30", tag="us-gaap:CashAndCashEquivalentsAtCarryingValue", form="Quarterly report", accession="0001628280-26-068246", section="Condensed Consolidated Balance Sheets", saved_line="113", source_file=QUARTERLY, source_line=113)),
        ("Net pension liabilities", "22", filing(token=token, unit="USD millions", period="2026-09-30", tag="net_pension_liabilities", form="Quarterly report", accession="0001628280-26-068246", section="Note 10", saved_line="1438", source_file=QUARTERLY, source_line=1438)),
        ("Operating-lease liabilities", "1,841", arithmetic(token=token, unit="USD millions", period="2026-09-30", operation="sum", inputs=["162", "1679"])),
        ("Transition Services Agreement expense", "30", filing(token=token, unit="USD millions", period="Four months ended 2026-09-30", tag="transition_services_expense", form="Quarterly report", accession="0001628280-26-068246", section="Note 12", saved_line="1571", source_file=QUARTERLY, source_line=1571)),
        ("Reported net income", "655", filing(token=token, unit="USD millions", period=fy, tag="us-gaap:NetIncomeLoss", form="Annual report", accession="0001628280-26-053359", section="Consolidated Statements of Income", saved_line="1583", source_file=ANNUAL, source_line=1583)),
        ("One-time separation", "492", filing(token=token, unit="USD millions", period=fy, tag="separation_and_other_costs", form="Annual report", accession="0001628280-26-053359", section="MD&A", saved_line="866", source_file=ANNUAL, source_line=866)),
        ("Effective tax rate", "25.9%", filing(token=token, unit="percent", period=fy, tag="effective_tax_rate", form="Annual report", accession="0001628280-26-053359", section="MD&A—Income Taxes", saved_line="1038", source_file=ANNUAL, source_line=1038)),
        ("After-tax one-time-cost adjustment", "492", filing(token=token, unit="USD millions", period=fy, tag="separation_and_other_costs", form="Annual report", accession="0001628280-26-053359", section="MD&A", saved_line="866", source_file=ANNUAL, source_line=866)),
        ("After-tax one-time-cost adjustment", "1", arithmetic(token=token, unit="constant", period=fy, operation="identity", inputs=["1"])),
        ("After-tax one-time-cost adjustment", "0.259", arithmetic(token=token, unit="decimal tax rate", period=fy, operation="divide", inputs=["25.9", "100"])),
        ("After-tax one-time-cost adjustment", "364.572", arithmetic(token=token, unit="USD millions", period=fy, operation="multiply_one_minus", inputs=["492", "0.259"])),
        ("Adjusted after-tax earnings", "655", filing(token=token, unit="USD millions", period=fy, tag="us-gaap:NetIncomeLoss", form="Annual report", accession="0001628280-26-053359", section="Consolidated Statements of Income", saved_line="1583", source_file=ANNUAL, source_line=1583)),
        ("Adjusted after-tax earnings", "364.572", arithmetic(token=token, unit="USD millions", period=fy, operation="multiply_one_minus", inputs=["492", "0.259"])),
        ("Adjusted after-tax earnings", "1,019.572", arithmetic(token=token, unit="USD millions", period=fy, operation="sum", inputs=["655", "364.572"])),
        ("Depreciation and amortization", "449", filing(token=token, unit="USD millions", period=fy, tag="us-gaap:DepreciationDepletionAndAmortization", form="Annual report", accession="0001628280-26-053359", section="Consolidated Statements of Cash Flows", saved_line="1632", source_file=ANNUAL, source_line=1632)),
        ("Capital expenditures", "379", filing(token=token, unit="USD millions", period=fy, tag="capital_expenditures", form="Annual report", accession="0001628280-26-053359", section="Consolidated Statements of Cash Flows", saved_line="1699", source_file=ANNUAL, source_line=1699)),
        ("Owner cash flow:", "1,019.572", arithmetic(token=token, unit="USD millions", period=fy, operation="sum", inputs=["655", "364.572"])),
        ("Owner cash flow:", "449", filing(token=token, unit="USD millions", period=fy, tag="us-gaap:DepreciationDepletionAndAmortization", form="Annual report", accession="0001628280-26-053359", section="Consolidated Statements of Cash Flows", saved_line="1632", source_file=ANNUAL, source_line=1632)),
        ("Owner cash flow:", "379", filing(token=token, unit="USD millions", period=fy, tag="capital_expenditures", form="Annual report", accession="0001628280-26-053359", section="Consolidated Statements of Cash Flows", saved_line="1699", source_file=ANNUAL, source_line=1699)),
        ("Owner cash flow:", "1,089.572", arithmetic(token=token, unit="USD millions", period=fy, operation="a_plus_b_minus_c", inputs=["1019.572", "449", "379"])),
        ("Primary diluted denominator", "149.9", filing(token=token, unit="million diluted shares", period="Four months ended 2026-09-30", tag="us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", form="Quarterly report", accession="0001628280-26-068246", section="Condensed Consolidated Statements of Income", saved_line="393", source_file=QUARTERLY, source_line=393)),
        ("Severe-stress value", "10.00", human(token=token, unit="owner-cash-flow multiple", period=fy, key="stress_multiple")),
        ("Severe-stress value", "72.69", arithmetic(token=token, unit="USD per diluted share", period=fy, operation="multiply_divide", inputs=["1089.572", "10.00", "149.9"], round_places=2)),
        ("Approved low value", "14.00", human(token=token, unit="owner-cash-flow multiple", period=fy, key="low_multiple")),
        ("Approved low value", "101.76", arithmetic(token=token, unit="USD per diluted share", period=fy, operation="multiply_divide", inputs=["1089.572", "14.00", "149.9"], round_places=2)),
        ("Approved mid value", "18.75", human(token=token, unit="owner-cash-flow multiple", period=fy, key="mid_multiple")),
        ("Approved mid value", "136.29", arithmetic(token=token, unit="USD per diluted share", period=fy, operation="multiply_divide", inputs=["1089.572", "18.75", "149.9"], round_places=2)),
        ("Supplemental-high value", "28.00", human(token=token, unit="owner-cash-flow multiple", period=fy, key="high_multiple")),
        ("Supplemental-high value", "203.52", arithmetic(token=token, unit="USD per diluted share", period=fy, operation="multiply_divide", inputs=["1089.572", "28.00", "149.9"], round_places=2)),
        ("Official close:", "126.58", official_price(token)),
        ("Observation window", "30", market_metric(token=token, unit="regular trading sessions", period="2026-10-09 through 2026-11-19", metric="observation_count")),
        ("Median daily dollar volume", "149,976,756.72", market_metric(token=token, unit="USD per day", period="30 regular trading sessions through 2026-11-19", metric="median_daily_dollar_volume")),
        ("Intended purchase", "500,000", human(token=token, unit="USD", period="Frozen Week 4 client configuration", key="intended_purchase_size_usd")),
        ("Maximum approved purchase fraction", "5.00%", human(token=token, unit="percent of median daily dollar volume", period="Frozen Week 4 client configuration", key="maximum_purchase_fraction_percent")),
        ("Required median daily dollar volume", "10,000,000", arithmetic(token=token, unit="USD per day", period="Frozen Week 4 client configuration", operation="divide", inputs=["500000", "0.05"])),
        ("Intended purchase as a fraction", "0.3334%", arithmetic(token=token, unit="percent of median daily dollar volume", period="30 regular trading sessions through 2026-11-19", operation="percentage", inputs=["500000", "149976756.72"], round_places=4)),
        ("Deciding number", "101.76", arithmetic(token=token, unit="USD per diluted share", period="2026-11-19", operation="multiply_divide", inputs=["1089.572", "14.00", "149.9"], round_places=2)),
        ("Deciding number", "126.58", official_price(token)),
        ("Deciding number", "24.82", arithmetic(token=token, unit="USD per diluted share", period="2026-11-19", operation="absolute_difference", inputs=["101.76", "126.58"], round_places=2)),
    ]
    for phrase, expected_token, claim in specs:
        if phrase in line and token == expected_token:
            return claim
    return None


def build() -> dict[str, object]:
    claims: list[dict[str, object]] = []
    failures: list[str] = []
    for line_number, line in enumerate(WORKSHEET.read_text(encoding="utf-8").splitlines(), start=1):
        saved_line_position = line.find("saved line")
        for index, match in enumerate(TOKEN_PATTERN.finditer(line), start=1):
            token = match.group(0)
            claim: dict[str, object] | None
            if ACCESSION_PATTERN.fullmatch(token):
                claim = {"kind": "accession"}
            elif DATE_PATTERN.fullmatch(token):
                claim = {"kind": "date"}
            elif saved_line_position >= 0 and match.start() > saved_line_position:
                claim = {"kind": "line_number"}
            else:
                claim = explicit_claim(line, token)
            if claim is None:
                failures.append(f"line {line_number}: {token} :: {line}")
                continue
            claim = {
                "id": f"L{line_number:03d}_T{index:02d}",
                "worksheet_line": line_number,
                "token": token,
                **claim,
            }
            claims.append(claim)
    if failures:
        raise SystemExit("Unclassified tokens:\n" + "\n".join(failures))
    return {
        "worksheet_file": "worksheet.md",
        "numeric_claims": claims,
    }


if __name__ == "__main__":
    (BASE / "worksheet.json").write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
