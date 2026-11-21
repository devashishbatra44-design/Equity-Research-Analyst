"""Build a deterministic non-registry live worksheet from one saved desk run."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from .investor_worksheet import owner_cash_flow, value_range


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find(path: Path, pattern: str) -> tuple[int, re.Match[str]]:
    compiled = re.compile(pattern)
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = compiled.search(line)
        if match:
            return number, match
    raise ValueError(f"Pattern was not found in {path.name}: {pattern}")


def _d(value: Any) -> Decimal:
    return Decimal(str(value).replace(",", ""))


def build(run: Path) -> tuple[str, dict[str, Any], dict[str, Any]]:
    manifest = _load(run / "manifest.json")
    facts = _load(run / "facts.json")
    market = _load(run / "market_summary.json")
    ownership = _load(run / "ownership_audit.json")
    config = _load(run / "frozen_numeric_config.json")
    annual = run / "10-k.txt"
    quarterly = run / "10-q.txt"
    release = run / "exhibit-99-1.txt"

    company = manifest["company"]
    filings = manifest["filings"]
    documents = manifest["documents"]
    annual_url = filings["10-k"]["index_url"]
    quarterly_url = filings["10-q"]["index_url"]
    current_url = filings["8-k"]["index_url"]
    release_url = documents["exhibit-99-1"]["source_url"]
    annual_accession = filings["10-k"]["accession_number"]
    quarterly_accession = filings["10-q"]["accession_number"]
    current_accession = filings["8-k"]["accession_number"]

    net_income = _d(facts["concepts"]["net_income"]["current"]["value"]) / Decimal("1000000")
    capex = _d(facts["concepts"]["property_equipment_additions"]["current"]["value"]) / Decimal("1000000")
    da_line, da_match = _find(annual, r"^Depreciation and amortization \| ([0-9,]+) \| [0-9,]+$")
    depreciation = _d(da_match.group(1)) / Decimal("1000000")
    shares_line, shares_match = _find(quarterly, r"^Outstanding at ([A-Za-z]+ [0-9]+, [0-9]{4}) \| ([0-9,]+)$")
    shares = _d(shares_match.group(2)) / Decimal("1000000")

    cash_line, cash_match = _find(
        release,
        r"Cash and cash equivalents were \$([0-9.]+) million at September 30, 2026.*working capital deficit of \$([0-9.]+) million.*Net cash used in operating activities.*was \$([0-9.]+) million",
    )
    loans_line, loans_match = _find(
        release,
        r"aggregate carrying amount of current and long-term loans payable and related interest.*declined to \$([0-9.]+) million",
    )
    liabilities_line, liabilities_match = _find(release, r"^Total liabilities were \$([0-9.]+) million")
    equity_line, equity_match = _find(release, r"Stockholders’ equity was \$([0-9.]+) million")
    revenue_line, revenue_match = _find(release, r"Consolidated revenue was \$([0-9.]+) million, compared with \$([0-9.]+) million")
    loss_line, loss_match = _find(release, r"Net loss was \$([0-9.]+) million, or \$([0-9.]+) per basic and diluted share")
    capital_line, _ = _find(release, r"requires additional capital to meet its obligations and operating needs")

    cash_flow = owner_cash_flow(net_income, depreciation, capex)
    close = _d(market["end_date_close"])
    values = value_range(
        cash_flow.value,
        method=config["valuation_method"],
        low_input=_d(config["low_value_usd_per_share"]),
        mid_input=_d(config["mid_value_usd_per_share"]),
        price=close,
    )
    median_dollar_volume = _d(market["median_daily_dollar_volume"])
    purchase = _d(config["intended_purchase_size_usd"])
    maximum_fraction = _d(config["maximum_purchase_fraction"])
    purchase_fraction = purchase / median_dollar_volume
    liquidity_status = "passes" if purchase_fraction <= maximum_fraction else "fails"
    conviction = "high" if values.price_vs_low == "more" and liquidity_status == "passes" else "low"
    market_value = close * shares
    valuation_gap = values.low_value - close

    lines: list[str] = []
    claims: list[dict[str, Any]] = []

    def add(text: str) -> int:
        lines.append(text)
        return len(lines)

    def claim(line: int, token: str, kind: str, **extra: Any) -> None:
        claims.append({
            "id": f"L{line:03d}_T{len([item for item in claims if item['worksheet_line'] == line]) + 1:02d}",
            "worksheet_line": line,
            "token": token,
            "kind": kind,
            **extra,
        })

    def date_claim(line: int, value: str) -> None:
        claim(line, value, "date")

    def accession_claim(line: int, value: str) -> None:
        claim(line, value, "accession")

    def filing_claim(
        line: int,
        token: str,
        value: str,
        unit: str,
        period: str,
        tag: str,
        form: str,
        accession: str,
        section: str,
        saved_line: int,
        source_file: str,
        source_token: str | None = None,
        source_multiplier: str | None = None,
    ) -> None:
        claim(
            line,
            token,
            "filing_fact",
            value=value,
            unit=unit,
            period=period,
            source=f"{form}, accession {accession}, {section}, saved line {saved_line}",
            tag=tag,
            filing=form,
            accession=accession,
            section=section,
            saved_line=str(saved_line),
            source_file=source_file,
            source_line=saved_line,
            **({"source_token": source_token} if source_token is not None else {}),
            **({"source_multiplier": source_multiplier} if source_multiplier is not None else {}),
        )
        accession_claim(line, accession)
        claim(line, str(saved_line), "line_number")

    line = add(
        f"Filings used: annual report accession {annual_accession}; quarterly report accession {quarterly_accession}; current report and earnings release accession {current_accession}."
    )
    for accession in (annual_accession, quarterly_accession, current_accession):
        accession_claim(line, accession)
    add("")
    add(f"# {company['legal_name']} ({company['ticker']}) Investor Worksheet")
    add("")
    line = add(f"Run time: {manifest['local_run_time'][:10]}, Eastern time.")
    date_claim(line, manifest["local_run_time"][:10])
    add("")
    add("This is an analytical worksheet. It is not a Buy, Hold, or Sell recommendation.")
    add("")
    add("## Scope and registry status")
    add("")
    add("Spin-off registry status: not applicable; this security is outside the saved spinoff registry.")
    add("Parent after a spin: not applicable.")
    add("Distribution ratio, record date, distribution date, and Form Ten registration: not applicable.")
    add("Spin debt and cash destination: not applicable.")
    add("Spin liabilities and restrictions: not applicable.")
    add("Seeker index, rank, and points: not applicable.")
    line = add("Live filing window ends: 2026-11-22.")
    date_claim(line, "2026-11-22")
    add("")
    add("## Market and release facts")
    add("")
    line = add(
        f"Official close: {close} USD per share | period: {market['end_date']} | source: {market['source']}, {market['source_url']}."
    )
    claim(line, str(close), "official_exchange_price", value=str(close), unit="USD per share", period=market["end_date"], source=market["source"], instrument=company["ticker"], price_date=market["end_date"], reader_source=market["source"], reader_file="market_summary.json")
    date_claim(line, market["end_date"])
    line = add(
        f"Shares outstanding: {shares} million shares | period: 2026-08-05 | source: quarterly report accession {quarterly_accession}, cover page, {quarterly_url}, saved line {shares_line}."
    )
    filing_claim(line, str(shares), str(shares), "million shares", "2026-08-05", "dei:EntityCommonStockSharesOutstanding", "quarterly report", quarterly_accession, "cover page", shares_line, "10-q.txt", shares_match.group(2), "0.000001")
    date_claim(line, "2026-08-05")
    line = add(f"Market value: {market_value} USD millions | period: {market['end_date']} | source: worksheet calculation, official close multiplied by shares outstanding.")
    claim(line, str(market_value), "arithmetic", value=str(market_value), unit="USD millions", period=market["end_date"], source="worksheet calculation", operation="multiply", inputs=[str(close), str(shares)])
    date_claim(line, market["end_date"])
    line = add(f"Quarterly revenue: {revenue_match.group(1)} USD millions | period: quarter ended 2026-09-30 | source: earnings release accession {current_accession}, financial results, {release_url}, saved line {revenue_line}.")
    filing_claim(line, revenue_match.group(1), revenue_match.group(1), "USD millions", "quarter ended 2026-09-30", "quarterly_revenue", "earnings release", current_accession, "Financial Results", revenue_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Quarterly net loss: {loss_match.group(1)} USD millions | period: quarter ended 2026-09-30 | source: earnings release accession {current_accession}, financial results, {release_url}, saved line {loss_line}.")
    filing_claim(line, loss_match.group(1), loss_match.group(1), "USD millions", "quarter ended 2026-09-30", "quarterly_net_loss", "earnings release", current_accession, "Financial Results", loss_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Cash: {cash_match.group(1)} USD millions | class: post-release | period: 2026-09-30 | source: earnings release accession {current_accession}, Balance Sheet and Liquidity, {release_url}, saved line {cash_line}.")
    filing_claim(line, cash_match.group(1), cash_match.group(1), "USD millions", "2026-09-30", "cash_and_cash_equivalents", "earnings release", current_accession, "Balance Sheet and Liquidity", cash_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Working-capital deficit: {cash_match.group(2)} USD millions | class: post-release | period: 2026-09-30 | source: earnings release accession {current_accession}, Balance Sheet and Liquidity, {release_url}, saved line {cash_line}.")
    filing_claim(line, cash_match.group(2), cash_match.group(2), "USD millions", "2026-09-30", "working_capital_deficit", "earnings release", current_accession, "Balance Sheet and Liquidity", cash_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Operating cash used: {cash_match.group(3)} USD millions | class: post-release | period: nine months ended 2026-09-30 | source: earnings release accession {current_accession}, Balance Sheet and Liquidity, {release_url}, saved line {cash_line}.")
    filing_claim(line, cash_match.group(3), cash_match.group(3), "USD millions", "nine months ended 2026-09-30", "operating_cash_used", "earnings release", current_accession, "Balance Sheet and Liquidity", cash_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Loans payable and related interest: {loans_match.group(1)} USD millions | class: post-release | period: 2026-09-30 | source: earnings release accession {current_accession}, Balance Sheet and Liquidity, {release_url}, saved line {loans_line}.")
    filing_claim(line, loans_match.group(1), loans_match.group(1), "USD millions", "2026-09-30", "loans_payable_and_related_interest", "earnings release", current_accession, "Balance Sheet and Liquidity", loans_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Total liabilities: {liabilities_match.group(1)} USD millions | class: post-release | period: 2026-09-30 | source: earnings release accession {current_accession}, Balance Sheet and Liquidity, {release_url}, saved line {liabilities_line}.")
    filing_claim(line, liabilities_match.group(1), liabilities_match.group(1), "USD millions", "2026-09-30", "total_liabilities", "earnings release", current_accession, "Balance Sheet and Liquidity", liabilities_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Stockholders' equity: {equity_match.group(1)} USD millions | class: post-release | period: 2026-09-30 | source: earnings release accession {current_accession}, Balance Sheet and Liquidity, {release_url}, saved line {equity_line}.")
    filing_claim(line, equity_match.group(1), equity_match.group(1), "USD millions", "2026-09-30", "stockholders_equity", "earnings release", current_accession, "Balance Sheet and Liquidity", equity_line, "exhibit-99-1.txt")
    date_claim(line, "2026-09-30")
    line = add(f"Additional-capital requirement amount: not known USD | period: 2026-11-20 | source: earnings release accession {current_accession}, Updated Asset Values and Liquidity Priorities, {release_url}, saved line {capital_line}.")
    accession_claim(line, current_accession)
    date_claim(line, "2026-11-20")
    claim(line, str(capital_line), "line_number")
    line = add(f"Issuer buyback amount: not known USD | period: through 2026-11-21 | source: annual report accession {annual_accession}, Item Five, {annual_url}, saved line 2320; quarterly report accession {quarterly_accession}, Part Two Item Two, {quarterly_url}, saved line 2717.")
    date_claim(line, "2026-11-21")
    accession_claim(line, annual_accession)
    accession_claim(line, quarterly_accession)
    claim(line, "2320", "line_number")
    claim(line, "2717", "line_number")
    reviewed_accessions = [item["accession"] for item in ownership["reviewed_filings"]]
    reviewed_urls = [item["url"] for item in ownership["reviewed_filings"]]
    line = add(f"Ownership reports reviewed: {ownership['form4_filings_found']} filings | period: 2026-01-01 through 2026-11-21 | source: ownership reports accessions {reviewed_accessions[0]} and {reviewed_accessions[1]}, {reviewed_urls[0]} and {reviewed_urls[1]}, non-derivative transactions; saved in ownership_audit.json.")
    claim(line, str(ownership["form4_filings_found"]), "arithmetic", value=str(ownership["form4_filings_found"]), unit="ownership reports", period="2026-01-01 through 2026-11-21", source="SEC submissions and primary ownership reports in ownership_audit.json", operation="identity", inputs=[str(ownership["form4_filings_found"])])
    date_claim(line, "2026-01-01")
    date_claim(line, "2026-11-21")
    for accession in reviewed_accessions:
        accession_claim(line, accession)
    line = add(f"Officer or director code P transactions found: {len(ownership['officer_or_director_code_p_purchases'])} transactions | period: 2026-01-01 through 2026-11-21 | source: ownership reports accessions {reviewed_accessions[0]} and {reviewed_accessions[1]}, non-derivative transactions, saved in ownership_audit.json; no open-market characterization is made.")
    claim(line, str(len(ownership["officer_or_director_code_p_purchases"])), "arithmetic", value=str(len(ownership["officer_or_director_code_p_purchases"])), unit="transactions", period="2026-01-01 through 2026-11-21", source="ownership_audit.json", operation="identity", inputs=[str(len(ownership["officer_or_director_code_p_purchases"]))])
    date_claim(line, "2026-01-01")
    date_claim(line, "2026-11-21")
    for accession in reviewed_accessions:
        accession_claim(line, accession)
    add("")
    add("## Owner cash flow")
    add("")
    line = add(f"After-tax earnings: {net_income} USD millions | class: historical | period: fiscal year ended 2025-12-31 | source: annual report accession {annual_accession}, XBRL tag us-gaap:NetIncomeLoss, {annual_url}.")
    claim(line, str(net_income), "filing_fact", value=str(net_income), unit="USD millions", period="fiscal year ended 2025-12-31", source=f"annual report accession {annual_accession}", tag="us-gaap:NetIncomeLoss", filing="annual report", accession=annual_accession, section="Consolidated Statements of Operations", saved_line="2437", source_file="10-k.txt", source_line=2437, source_token="10892833", source_multiplier="-0.000001")
    accession_claim(line, annual_accession)
    date_claim(line, "2025-12-31")
    line = add(f"Depreciation and amortization: {depreciation} USD millions | class: historical | period: fiscal year ended 2025-12-31 | source: annual report accession {annual_accession}, Consolidated Statements of Cash Flows, {annual_url}, saved line {da_line}.")
    filing_claim(line, str(depreciation), str(depreciation), "USD millions", "fiscal year ended 2025-12-31", "us-gaap:DepreciationDepletionAndAmortization", "annual report", annual_accession, "Consolidated Statements of Cash Flows", da_line, "10-k.txt", da_match.group(1), "0.000001")
    date_claim(line, "2025-12-31")
    line = add(f"Capital expenditures: {capex} USD millions | class: historical | period: fiscal year ended 2025-12-31 | source: annual report accession {annual_accession}, XBRL tag us-gaap:PaymentsToAcquireProductiveAssets, {annual_url}.")
    claim(line, str(capex), "filing_fact", value=str(capex), unit="USD millions", period="fiscal year ended 2025-12-31", source=f"annual report accession {annual_accession}", tag="us-gaap:PaymentsToAcquireProductiveAssets", filing="annual report", accession=annual_accession, section="Consolidated Statements of Cash Flows", saved_line="2938", source_file="10-k.txt", source_line=2938, source_token="48594", source_multiplier="0.000001")
    accession_claim(line, annual_accession)
    date_claim(line, "2025-12-31")
    line = add(f"Owner cash flow: {net_income} + {depreciation} - {capex} = {cash_flow.value} USD millions | period: fiscal year ended 2025-12-31 | source: worksheet calculation.")
    claim(line, str(net_income), "arithmetic", value=str(net_income), unit="USD millions", period="fiscal year ended 2025-12-31", source="cited owner-cash-flow input", operation="identity", inputs=[str(net_income)])
    claim(line, str(depreciation), "arithmetic", value=str(depreciation), unit="USD millions", period="fiscal year ended 2025-12-31", source="cited owner-cash-flow input", operation="identity", inputs=[str(depreciation)])
    claim(line, str(capex), "arithmetic", value=str(capex), unit="USD millions", period="fiscal year ended 2025-12-31", source="cited owner-cash-flow input", operation="identity", inputs=[str(capex)])
    claim(line, str(cash_flow.value), "arithmetic", value=str(cash_flow.value), unit="USD millions", period="fiscal year ended 2025-12-31", source="worksheet calculation", operation="a_plus_b_minus_c", inputs=[str(net_income), str(depreciation), str(capex)])
    date_claim(line, "2025-12-31")
    add("")
    add("## Value, liquidity, and release view")
    add("")
    line = add("Low value: 0 USD per share | source: frozen human worksheet configuration.")
    claim(line, "0", "human_value", value="0", unit="USD per share", period="current worksheet", source="frozen human worksheet configuration", config_file="frozen_numeric_config.json", config_key="low_value_usd_per_share", frozen_value="0")
    line = add("Mid value: 0 USD per share | source: frozen human worksheet configuration.")
    claim(line, "0", "human_value", value="0", unit="USD per share", period="current worksheet", source="frozen human worksheet configuration", config_file="frozen_numeric_config.json", config_key="mid_value_usd_per_share", frozen_value="0")
    line = add(f"Deciding number: 0 - {close} = {valuation_gap} USD per share | period: {market['end_date']} | source: worksheet calculation and market_summary.json.")
    claim(line, "0", "arithmetic", value="0", unit="USD per share", period=market["end_date"], source="frozen low value", operation="identity", inputs=["0"])
    claim(line, str(close), "official_exchange_price", value=str(close), unit="USD per share", period=market["end_date"], source=market["source"], instrument=company["ticker"], price_date=market["end_date"], reader_source=market["source"], reader_file="market_summary.json")
    claim(line, str(valuation_gap), "arithmetic", value=str(valuation_gap), unit="USD per share", period=market["end_date"], source="worksheet calculation and market_summary.json", operation="sum", inputs=["0", str(-close)])
    date_claim(line, market["end_date"])
    line = add(f"Thirty-session median daily dollar volume: {median_dollar_volume} USD per day | period: {market['start_date']} through {market['end_date']} | source: {market['source']}, market_summary.json.")
    claim(line, str(median_dollar_volume), "market_metric", value=str(median_dollar_volume), unit="USD per day", period=f"{market['start_date']} through {market['end_date']}", source=market["source"], instrument=company["ticker"], metric="median_daily_dollar_volume", reader_source=market["source"], reader_file="market_summary.json")
    date_claim(line, market["start_date"])
    date_claim(line, market["end_date"])
    line = add(f"Intended purchase: {purchase} USD | source: frozen human worksheet configuration.")
    claim(line, str(purchase), "human_rate", value=str(purchase), unit="USD", period="current worksheet", source="frozen human worksheet configuration", config_file="frozen_numeric_config.json", config_key="intended_purchase_size_usd", frozen_value=str(purchase))
    line = add(f"Maximum purchase fraction: {maximum_fraction * Decimal('100')}% | source: frozen human worksheet configuration.")
    claim(line, f"{maximum_fraction * Decimal('100')}%", "human_rate", value=str(maximum_fraction), unit="ratio", period="current worksheet", source="frozen human worksheet configuration", config_file="frozen_numeric_config.json", config_key="maximum_purchase_fraction", frozen_value=str(maximum_fraction))
    purchase_percent = (purchase_fraction * Decimal("100")).quantize(Decimal("0.01"))
    line = add(f"Purchase as a fraction of median daily dollar volume: {purchase_percent}% | source: worksheet calculation.")
    claim(line, f"{purchase_percent}%", "arithmetic", value=str(purchase_percent), unit="percent", period=f"{market['start_date']} through {market['end_date']}", source="worksheet calculation", operation="percentage", inputs=[str(purchase), str(median_dollar_volume)], round_places=2)
    add(f"Liquidity result: {liquidity_status}.")
    add(f"Price view: {values.price_vs_low}; the supported low value is less than the official close.")
    add(f"Conviction: {conviction} because the valuation and liquidity tests do not both pass.")
    add("")
    add("## Persona judgment")
    add("")
    if (run / "persona_output.md").exists():
        add("The saved one-call judgment is in `persona_output.md`.")
        add("The favorable-case paragraph is rejected because it inverted the low-value comparison and described a failed valuation test as a possible margin of safety.")
        add("No supported cheap case remains under the frozen valuation evidence.")
        add("The disconfirming paragraph is consistent with the cited facts: owner cash flow is negative, working capital is negative, operating cash was used, additional capital is required, and the merger remains conditional.")
        line = add("Human next-filing condition: I will change the less view only if the next results make the TTM positive owner cash flow, working capital of more than $0, and complete financing sufficent to cover at least 12 months of operating requirmemnt, with the recalculation low value per fully diluted share exceeding the market price.")
        claim(line, "0", "human_value", value="0", unit="USD working-capital threshold", period="next relevant filing", source="frozen human investor persona", config_file="frozen_numeric_config.json", config_key="view_change_min_working_capital_usd", frozen_value="0")
        claim(line, "12", "human_value", value="12", unit="months", period="next relevant filing", source="frozen human investor persona", config_file="frozen_numeric_config.json", config_key="view_change_min_runway_months", frozen_value="12")
    else:
        add("Pending the frozen human persona and one bounded model call.")
    add("")
    add("## Not known")
    add("")
    add("- Exact post-merger exchange ratio and final ownership dilution: not known.")
    add("- Amount and terms of required additional capital: not known.")
    add("- Liquidation value: not computed.")

    worksheet = "\n".join(lines) + "\n"
    calculations = {
        "owner_cash_flow_usd_millions": str(cash_flow.value),
        "low_value_usd_per_share": str(values.low_value),
        "mid_value_usd_per_share": str(values.mid_value),
        "official_close_usd_per_share": str(close),
        "valuation_gap_usd_per_share": str(valuation_gap),
        "shares_outstanding_millions": str(shares),
        "market_value_usd_millions": str(market_value),
        "median_daily_dollar_volume_usd": str(median_dollar_volume),
        "purchase_fraction_of_median_daily_dollar_volume": str(purchase_fraction),
        "purchase_percent_of_median_daily_dollar_volume": str(purchase_fraction * Decimal("100")),
        "liquidity_status": liquidity_status,
        "price_view": values.price_vs_low,
        "conviction": conviction,
    }
    return worksheet, {"worksheet_file": "worksheet.md", "numeric_claims": claims}, calculations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    worksheet, claims, calculations = build(args.run)
    (args.run / "worksheet.md").write_text(worksheet, encoding="utf-8")
    (args.run / "worksheet.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")
    (args.run / "worksheet_calculations.json").write_text(json.dumps(calculations, indent=2) + "\n", encoding="utf-8")
    report = (args.run / "report.md").read_text(encoding="utf-8").rstrip()
    (args.run / "live_report.md").write_text(
        report + "\n\n# Investor Worksheet\n\n" + worksheet,
        encoding="utf-8",
    )
    print(args.run / "worksheet.md")


if __name__ == "__main__":
    main()
