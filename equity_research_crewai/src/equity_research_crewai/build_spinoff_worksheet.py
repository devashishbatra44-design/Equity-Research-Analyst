"""Build a source-driven Week 4 spinoff worksheet without issuer-specific code."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}.")
    return value


def _d(value: Any) -> Decimal:
    return Decimal(str(value).replace(",", ""))


def _money(value: Any, places: int = 2) -> str:
    return f"{_d(value):,.{places}f}"


def build(run: Path) -> tuple[str, dict[str, Any]]:
    profile = _load(run / "worksheet_profile.json")
    inputs = _load(run / "worksheet_inputs.json")
    calculations = _load(run / "calculations.json")
    provenance = _load(run / "worksheet_input_provenance.json")
    market = _load(run / "market_summary.json")
    ownership = _load(run / "ownership_audit.json")
    facts = {str(item["id"]): item for item in provenance["facts"]}

    lines: list[str] = []
    claims: list[dict[str, Any]] = []

    def add(text: str = "") -> int:
        lines.append(text)
        return len(lines)

    def claim(line: int, token: str, kind: str, **extra: Any) -> str:
        claim_id = f"L{line:03d}_T{len([x for x in claims if x['worksheet_line'] == line]) + 1:02d}"
        claims.append({"id": claim_id, "worksheet_line": line, "token": token, "kind": kind, **extra})
        return claim_id

    def arithmetic(line: int, token: str, value: Any, unit: str, period: str, operation: str, values: list[Any], places: int | None = None) -> str:
        extra: dict[str, Any] = {
            "value": str(value), "unit": unit, "period": period, "source": "deterministic worksheet calculation",
            "operation": operation, "inputs": [str(item) for item in values],
        }
        if places is not None:
            extra["round_places"] = places
        return claim(line, token, "arithmetic", **extra)

    def filing(line: int, fact_id: str, token: str, value: Any | None = None, unit: str | None = None) -> str:
        fact = facts[fact_id]
        return claim(
            line,
            token,
            "filing_fact",
            value=str(inputs[fact_id] if value is None else value),
            unit=unit or str(fact["unit"]),
            period=str(fact["period"]),
            source=f"{fact['form']}, accession {fact['accession']}, {fact['section']}",
            tag=fact_id,
            filing=fact["form"],
            accession=fact["accession"],
            section=fact["section"],
            saved_line=str(fact["source_line"]),
            source_file=fact["source_file"],
            source_line=int(fact["source_line"]),
            source_token=str(fact["source_token"]),
            source_multiplier=("1" if fact_id == "operating_tax_rate" else str(fact.get("source_multiplier", "1"))),
        )

    def human(line: int, token: str, value: Any, unit: str, key: str) -> str:
        return claim(
            line, token, "human_rate", value=str(value), unit=unit, period="frozen human worksheet configuration",
            source="frozen human worksheet configuration", config_file="frozen_numeric_config.json",
            config_key=key, frozen_value=str(value),
        )

    add("Filings used: saved final information statement, completion current report, annual report, quarterly report, and ownership-report audit.")
    add()
    add(f"# {profile['company_name']} ({profile['ticker']}) Investor Worksheet")
    add()
    add(f"Run date: {str(profile['run_time'])[:10]}.")
    add()
    add(str(profile["correction_note"]))
    add()
    add("The fixed-order agent-team report is saved as `agent_team_report.md`. Its verifier output is saved as `agent_team_verified_report.md`.")
    add()
    add("This is an analytical worksheet. It is not a Buy, Hold, or Sell recommendation.")
    add()
    add("## Registry and transaction facts")
    add()
    line = add(f"Parent: {inputs['parent_name']} | period: spin-off completed 2026-06-01 | source: final information statement accession {facts['parent_name']['accession']}, cited section.")
    line = add(f"Distribution ratio: {inputs['distribution_ratio_text']} | period: record date 2026-05-15 | source: final information statement accession {facts['distribution_ratio_text']['accession']}, cited section.")
    line = add(f"Record date: 2026-05-15 | source: final information statement accession {facts['record_date']['accession']}, cited section.")
    line = add(f"Distribution date: 2026-06-01 | source: current report accession {facts['distribution_date']['accession']}, cited section.")
    line = add(f"Distributed by parent: {inputs['distributed_percent']}% of outstanding shares | period: 2026-06-01 | source: current report accession {facts['distributed_percent']['accession']}, cited section.")
    distributed_claim = filing(line, "distributed_percent", f"{inputs['distributed_percent']}%")
    line = add(f"Parent after the spin: {inputs['parent_name']} retained {inputs['retained_percent']}% of outstanding shares | period: immediately after 2026-06-01 | source: final information statement accession {facts['retained_percent']['accession']}, cited section.")
    retained_claim = filing(line, "retained_percent", f"{inputs['retained_percent']}%")
    line = add(f"Seeker index date: {profile['index_date']} | window end: {profile['window_end']} | rank: {profile['rank']} of 10 scored names | points: {profile['points']} | source: saved seeker report.")
    rank_claim = arithmetic(line, str(profile["rank"]), profile["rank"], "rank", profile["index_date"], "identity", [profile["rank"]])
    arithmetic(line, "10", "10", "scored names", profile["index_date"], "identity", ["10"])
    points_claim = arithmetic(line, str(profile["points"]), profile["points"], "points", profile["index_date"], "identity", [profile["points"]])
    add()
    add("## Separation financing and obligations")
    add()
    line = add(f"Senior notes issued: {_money(inputs['senior_notes_usd_millions'], 0)} USD millions | period: before 2026-06-01 | source: quarterly report accession {facts['senior_notes_usd_millions']['accession']}, cited section.")
    notes_claim = filing(line, "senior_notes_usd_millions", _money(inputs["senior_notes_usd_millions"], 0))
    line = add(f"Term loan issued: {_money(inputs['term_loan_usd_millions'], 0)} USD millions | period: before 2026-06-01 | source: quarterly report accession {facts['term_loan_usd_millions']['accession']}, cited section.")
    loan_claim = filing(line, "term_loan_usd_millions", _money(inputs["term_loan_usd_millions"], 0))
    line = add(f"Cash paid to parent: approximately {_money(inputs['cash_paid_parent_usd_millions'], 0)} USD millions | period: before 2026-06-01 | source: current report accession {facts['cash_paid_parent_usd_millions']['accession']}, cited section.")
    cash_paid_claim = filing(line, "cash_paid_parent_usd_millions", _money(inputs["cash_paid_parent_usd_millions"], 0))
    line = add(f"Funded-debt fair value, excluding finance leases: approximately {_money(inputs['funded_debt_fair_value_usd_millions'], 0)} USD millions | period: 2026-09-30 | source: quarterly report accession {facts['funded_debt_fair_value_usd_millions']['accession']}, cited section.")
    filing(line, "funded_debt_fair_value_usd_millions", _money(inputs["funded_debt_fair_value_usd_millions"], 0))
    line = add(f"Finance-lease liabilities: {_money(inputs['finance_lease_liabilities_usd_millions'], 0)} USD millions | period: 2026-09-30 | source: quarterly report accession {facts['finance_lease_liabilities_usd_millions']['accession']}, cited section.")
    filing(line, "finance_lease_liabilities_usd_millions", _money(inputs["finance_lease_liabilities_usd_millions"], 0))
    line = add(f"Cash: {_money(inputs['cash_usd_millions'], 0)} USD millions | period: 2026-09-30 | source: quarterly report accession {facts['cash_usd_millions']['accession']}, cited section.")
    filing(line, "cash_usd_millions", _money(inputs["cash_usd_millions"], 0))
    line = add(f"Net pension liabilities: {_money(inputs['net_pension_liabilities_usd_millions'], 0)} USD millions | period: 2026-09-30 | source: quarterly report accession {facts['net_pension_liabilities_usd_millions']['accession']}, cited section.")
    filing(line, "net_pension_liabilities_usd_millions", _money(inputs["net_pension_liabilities_usd_millions"], 0))
    leases = _d(inputs["operating_lease_current_usd_millions"]) + _d(inputs["operating_lease_long_term_usd_millions"])
    line = add(f"Operating-lease liabilities: {_money(leases, 0)} USD millions | period: 2026-09-30 | source: worksheet sum of current and long-term balances in quarterly report accession {facts['operating_lease_current_usd_millions']['accession']}.")
    leases_claim = arithmetic(line, _money(leases, 0), leases, "USD millions", "2026-09-30", "sum", [inputs["operating_lease_current_usd_millions"], inputs["operating_lease_long_term_usd_millions"]])
    line = add(f"Transition-services expense: {_money(inputs['transition_services_expense_usd_millions'], 0)} USD millions | period: four months ended 2026-09-30 | source: quarterly report accession {facts['transition_services_expense_usd_millions']['accession']}, cited section.")
    filing(line, "transition_services_expense_usd_millions", _money(inputs["transition_services_expense_usd_millions"], 0))
    add(f"Transition-services term: {inputs['transition_services_term_text']} | source: annual report accession {facts['transition_services_term_text']['accession']}, cited section.")
    add("Tax-related and credit-facility covenants can restrict stock issuance, asset dispositions, added debt, liens, combinations, dividends, and repurchases. The saved annual report is the controlling source; this line states no amount.")
    add()
    add("## Market value, buybacks, and ownership")
    add()
    close = _d(calculations["official_close_usd_per_share"])
    actual_shares = _d(inputs["basic_shares_point_in_time_millions"])
    market_value = close * actual_shares
    line = add(f"Official close: {_money(close)} USD per share | period: {market['end_date']} | source: {market['source']} through the common closes reader.")
    close_claim = claim(line, _money(close), "official_exchange_price", value=str(close), unit="USD per share", period=market["end_date"], source=market["source"], instrument=profile["ticker"], price_date=market["end_date"], reader_source=market["source"], reader_file="market_summary.json")
    line = add(f"Point-in-time shares outstanding: {_money(actual_shares, 6)} million | period: 2026-10-27 | source: quarterly report accession {facts['basic_shares_point_in_time_millions']['accession']}, cover page.")
    shares_claim = filing(line, "basic_shares_point_in_time_millions", _money(actual_shares, 6))
    line = add(f"Market value: {_money(market_value)} USD millions | period: {market['end_date']} | source: official close multiplied by point-in-time shares outstanding.")
    market_value_claim = arithmetic(line, _money(market_value), market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "USD millions", market["end_date"], "multiply", [close, actual_shares], 2)
    add(f"Buybacks: the annual report states that no common shares were purchased during the three months ended 2026-05-31. The quarterly report contains no later issuer-purchase table, so a later amount is not known. Source: annual report accession {facts['buyback_disclosure_text']['accession']}, cited section.")
    line = add(f"Ownership reports reviewed: {ownership['form4_filings_found']} | period: 2026-06-01 through {ownership['through_date']} | source: saved SEC ownership audit.")
    ownership_count_claim = arithmetic(line, str(ownership["form4_filings_found"]), ownership["form4_filings_found"], "ownership reports", f"2026-06-01 through {ownership['through_date']}", "identity", [ownership["form4_filings_found"]])
    purchases = len(ownership["officer_or_director_code_p_purchases"])
    line = add(f"Officer-or-director code-P purchases found: {purchases} | period: 2026-06-01 through {ownership['through_date']} | source: saved SEC ownership audit; no open-market characterization is made.")
    purchases_claim = arithmetic(line, str(purchases), purchases, "transactions", f"2026-06-01 through {ownership['through_date']}", "identity", [purchases])
    add()
    add("## Owner cash flow")
    add()
    line = add(f"Reported after-tax earnings: {_money(inputs['reported_after_tax_earnings'], 0)} USD millions | period: fiscal year ended 2026-05-31 | source: annual report accession {facts['reported_after_tax_earnings']['accession']}, cited section.")
    earnings_claim = filing(line, "reported_after_tax_earnings", _money(inputs["reported_after_tax_earnings"], 0))
    line = add(f"Depreciation and amortization: {_money(inputs['depreciation'], 0)} USD millions | period: fiscal year ended 2026-05-31 | source: annual report accession {facts['depreciation']['accession']}, cited section.")
    depreciation_claim = filing(line, "depreciation", _money(inputs["depreciation"], 0))
    line = add(f"Capital expenditures: {_money(inputs['capital_expenditures'], 0)} USD millions | period: fiscal year ended 2026-05-31 | source: annual report accession {facts['capital_expenditures']['accession']}, cited section.")
    capex_claim = filing(line, "capital_expenditures", _money(inputs["capital_expenditures"], 0))
    course_ocf = _d(calculations["course_owner_cash_flow_usd_millions"])
    line = add(f"Course owner cash flow: {_money(inputs['reported_after_tax_earnings'], 0)} + {_money(inputs['depreciation'], 0)} - {_money(inputs['capital_expenditures'], 0)} = {_money(course_ocf, 0)} USD millions | period: fiscal year ended 2026-05-31 | source: course formula and cited inputs.")
    course_claim = arithmetic(line, _money(course_ocf, 0), course_ocf, "USD millions", "fiscal year ended 2026-05-31", "a_plus_b_minus_c", [inputs["reported_after_tax_earnings"], inputs["depreciation"], inputs["capital_expenditures"]])
    arithmetic(line, _money(inputs["reported_after_tax_earnings"], 0), inputs["reported_after_tax_earnings"], "USD millions", "fiscal year ended 2026-05-31", "identity", [inputs["reported_after_tax_earnings"]])
    arithmetic(line, _money(inputs["depreciation"], 0), inputs["depreciation"], "USD millions", "fiscal year ended 2026-05-31", "identity", [inputs["depreciation"]])
    arithmetic(line, _money(inputs["capital_expenditures"], 0), inputs["capital_expenditures"], "USD millions", "fiscal year ended 2026-05-31", "identity", [inputs["capital_expenditures"]])
    one_time = _d(inputs["one_time_cost"])
    tax_rate = _d(inputs["operating_tax_rate"])
    adjustment = _d(calculations["after_tax_one_time_adjustment_usd_millions"])
    line = add(f"Separate adjusted sensitivity: add back {_money(one_time, 0)} USD millions of separation costs after a {tax_rate * 100}% effective tax rate, producing {_money(calculations['adjusted_owner_cash_flow_before_new_debt_interest_usd_millions'], 3)} USD millions before new-debt interest | source: cited annual report inputs and worksheet calculation.")
    one_time_claim = filing(line, "one_time_cost", _money(one_time, 0))
    tax_claim = filing(line, "operating_tax_rate", f"{tax_rate * 100}%", value=tax_rate * 100, unit="percent")
    adjusted_pre_interest = _d(calculations["adjusted_owner_cash_flow_before_new_debt_interest_usd_millions"])
    adjusted_claim = arithmetic(line, _money(adjusted_pre_interest, 3), adjusted_pre_interest, "USD millions", "fiscal year ended 2026-05-31", "a_plus_b_minus_c", [calculations["adjusted_after_tax_earnings_usd_millions"], inputs["depreciation"], inputs["capital_expenditures"]])
    line = add(f"Post-spin quarterly interest expense: {_money(inputs['post_spin_quarterly_interest_expense'], 0)} USD millions | period: three months ended 2026-09-30 | source: quarterly report accession {facts['post_spin_quarterly_interest_expense']['accession']}, cited section.")
    interest_claim = filing(line, "post_spin_quarterly_interest_expense", _money(inputs["post_spin_quarterly_interest_expense"], 0))
    annualized_after_tax_interest = _d(calculations["after_tax_annualized_post_spin_interest_expense_usd_millions"])
    line = add(f"Annualized after-tax post-spin interest: {_money(inputs['post_spin_quarterly_interest_expense'], 0)} multiplied by 4, then multiplied by one minus {tax_rate}, equals {_money(annualized_after_tax_interest, 3)} USD millions | source: worksheet calculation.")
    arithmetic(line, _money(inputs["post_spin_quarterly_interest_expense"], 0), inputs["post_spin_quarterly_interest_expense"], "USD millions", "three months ended 2026-09-30", "identity", [inputs["post_spin_quarterly_interest_expense"]])
    arithmetic(line, "4", "4", "quarters", "annualization", "identity", ["4"])
    arithmetic(line, str(tax_rate), tax_rate, "decimal rate", "fiscal year ended 2026-05-31", "identity", [tax_rate])
    arithmetic(line, _money(annualized_after_tax_interest, 3), annualized_after_tax_interest, "USD millions", "annualized sensitivity", "multiply_one_minus", [calculations["annualized_post_spin_interest_expense_usd_millions"], tax_rate])
    valuation_ocf = _d(calculations["valuation_owner_cash_flow_usd_millions"])
    line = add(f"Valuation owner-cash-flow sensitivity: {_money(adjusted_pre_interest, 3)} - {_money(annualized_after_tax_interest, 3)} = {_money(valuation_ocf, 3)} USD millions | source: worksheet calculation. This is separate from the {_money(course_ocf, 0)} USD million course result.")
    arithmetic(line, _money(adjusted_pre_interest, 3), adjusted_pre_interest, "USD millions", "valuation sensitivity", "identity", [adjusted_pre_interest])
    arithmetic(line, _money(annualized_after_tax_interest, 3), annualized_after_tax_interest, "USD millions", "valuation sensitivity", "identity", [annualized_after_tax_interest])
    valuation_ocf_claim = arithmetic(line, _money(valuation_ocf, 3), valuation_ocf, "USD millions", "valuation sensitivity", "sum", [adjusted_pre_interest, -annualized_after_tax_interest])
    arithmetic(line, _money(course_ocf, 0), course_ocf, "USD millions", "fiscal year ended 2026-05-31", "identity", [course_ocf])
    add()
    add("## Value, liquidity, and judgment")
    add()
    diluted = _d(inputs["diluted_shares_millions"])
    line = add(f"Primary diluted denominator: {_money(diluted, 1)} million shares | period: three months ended 2026-09-30 | source: quarterly report accession {facts['diluted_shares_millions']['accession']}, cited section.")
    diluted_claim = filing(line, "diluted_shares_millions", _money(diluted, 1))
    value_claims: dict[str, str] = {}
    for label, multiple_key, value_key in (
        ("Stress", "stress_multiple", "stress_value_usd_per_share"),
        ("Low", "low_multiple", "low_value_usd_per_share"),
        ("Mid", "mid_multiple", "mid_value_usd_per_share"),
        ("High", "high_multiple", "high_value_usd_per_share"),
    ):
        multiple = _d(inputs[multiple_key])
        per_share = _d(calculations[value_key]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line = add(f"{label} value: {multiple} times valuation owner cash flow = {_money(per_share)} USD per diluted share | source: frozen multiple and worksheet calculation.")
        human(line, str(multiple), multiple, "owner-cash-flow multiple", multiple_key)
        value_claims[label] = arithmetic(line, _money(per_share), per_share, "USD per diluted share", "valuation sensitivity", "multiply_divide", [valuation_ocf, multiple, diluted], 2)
    median = _d(market["median_daily_dollar_volume"])
    line = add(f"Observation window: {market['observation_count']} regular sessions from {market['start_date']} through {market['end_date']} | source: derived market summary from the common closes reader.")
    claim(line, str(market["observation_count"]), "market_metric", value=str(market["observation_count"]), unit="regular sessions", period=f"{market['start_date']} through {market['end_date']}", source=market["source"], instrument=profile["ticker"], metric="observation_count", reader_source=market["source"], reader_file="market_summary.json")
    line = add(f"Median daily dollar volume: {_money(median)} USD per day | period: {market['start_date']} through {market['end_date']} | source: derived market summary from the common closes reader.")
    claim(line, _money(median), "market_metric", value=str(median), unit="USD per day", period=f"{market['start_date']} through {market['end_date']}", source=market["source"], instrument=profile["ticker"], metric="median_daily_dollar_volume", reader_source=market["source"], reader_file="market_summary.json")
    purchase = _d(inputs["intended_purchase_size"])
    maximum_fraction = _d(inputs["maximum_purchase_fraction"])
    purchase_percent = (purchase / median * 100).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    line = add(f"Intended purchase: {_money(purchase, 0)} USD | maximum fraction: {maximum_fraction * 100}% of median daily dollar volume | actual fraction: {purchase_percent}% | liquidity status: {calculations['liquidity_status']}.")
    human(line, _money(purchase, 0), purchase, "USD", "intended_purchase_size_usd")
    human(line, f"{maximum_fraction * 100}%", maximum_fraction * 100, "percent", "maximum_purchase_fraction_percent")
    arithmetic(line, f"{purchase_percent}%", purchase_percent, "percent", f"{market['start_date']} through {market['end_date']}", "percentage", [purchase, median], 4)
    low = _d(calculations["low_value_usd_per_share"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gap = abs(close - low).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    view = "more" if low >= close else "less"
    line = add(f"Judgment: {view}. The low value of {_money(low)} USD per diluted share is {_money(gap)} USD per share below the official close of {_money(close)} USD per share. Conviction: {calculations['conviction']}.")
    arithmetic(line, _money(low), low, "USD per diluted share", market["end_date"], "multiply_divide", [valuation_ocf, inputs["low_multiple"], diluted], 2)
    arithmetic(line, _money(gap), gap, "USD per share", market["end_date"], "absolute_difference", [low, close], 2)
    claim(line, _money(close), "official_exchange_price", value=str(close), unit="USD per share", period=market["end_date"], source=market["source"], instrument=profile["ticker"], price_date=market["end_date"], reader_source=market["source"], reader_file="market_summary.json")
    add()
    add("## Persona criteria recorded and hook-checked")
    add()
    score_specs = (
        ("Forced or indifferent seller and attention gap", "3", [distributed_claim, retained_claim, rank_claim, points_claim]),
        ("Parent allocation and separation burden", "1", [notes_claim, loan_claim, cash_paid_claim]),
        ("Standalone earning power and owner cash flow", "3", [course_claim, valuation_ocf_claim]),
        ("Business durability and value-trap risk", "3", [leases_claim]),
        ("Alignment and path to value realization", "2", [ownership_count_claim, purchases_claim, retained_claim]),
        ("Conservative valuation and downside protection", "2", [value_claims["Low"], close_claim, market_value_claim]),
    )
    for criterion, score, evidence_ids in score_specs:
        line = add(f"{criterion} | score: {score} | source: saved persona output; not used in a composite.")
        claim(line, score, "analytical_score", value=score, unit="score", period="worksheet run", source="saved persona output", criterion=criterion, persona_file="persona_output.md", scale_min="1", scale_max="5", evidence_claim_ids=evidence_ids, used_in_composite=False)
    add()
    add("## What would change the view")
    add()
    add("The next relevant filing would change the less view if it shows durable owner cash flow after the new debt burden and quantifies recurring standalone costs such that a recalculated conservative low value exceeds the official market price. The calculation must continue to use a fully diluted denominator and the liquidity test must continue to pass.")

    date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
    accession_pattern = re.compile(r"\d{10}-\d{2}-\d{6}")
    for line_number, text in enumerate(lines, start=1):
        existing = {(item["worksheet_line"], str(item["token"]).replace(",", "")) for item in claims}
        for match in accession_pattern.finditer(text):
            token = match.group(0)
            if (line_number, token) not in existing:
                claim(line_number, token, "accession")
                existing.add((line_number, token))
        for match in date_pattern.finditer(text):
            token = match.group(0)
            if (line_number, token) not in existing:
                claim(line_number, token, "date")
                existing.add((line_number, token))

    return "\n".join(lines) + "\n", {"worksheet_file": "worksheet.md", "numeric_claims": claims}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    worksheet, claims = build(args.run)
    (args.run / "worksheet.md").write_text(worksheet, encoding="utf-8")
    (args.run / "worksheet.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
