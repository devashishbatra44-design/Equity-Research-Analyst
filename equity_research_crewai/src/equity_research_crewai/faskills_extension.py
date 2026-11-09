"""Course-safe deterministic metrics adapted from CinderZhang/FAskills v2.0.0.

The original project is MIT licensed:
https://github.com/CinderZhang/FAskills

This module keeps the useful Python-first calculation pattern. The graph routes
the nine frameworks as course-safe analytical lenses; it does not simulate
investor opinions, create price targets, or bypass the course Verifier.
Missing inputs remain unavailable. They never become zero silently.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


API_URL = "https://api.financialdatasets.ai/financials"
PROVIDER = "financialdatasets.ai"
ADAPTATION_SOURCE = "CinderZhang/FAskills v2.0.0"


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ZeroDivisionError("The denominator is zero.")
    return numerator / denominator


def _missing(rows: dict[str, dict[str, Any]], requirements: list[tuple[str, str]]) -> list[str]:
    missing: list[str] = []
    for row_name, field_name in requirements:
        if _number(rows[row_name], field_name) is None:
            missing.append(f"{row_name}.{field_name}")
    return missing


def _unavailable(name: str, formula: str, missing_fields: list[str], note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "validation_status": "unavailable",
        "value": None,
        "formula": formula,
        "inputs": {},
        "components": {},
        "interpretation": "Not calculated because required inputs are missing.",
        "warnings": [],
        "missing_fields": missing_fields,
        "note": note or None,
    }


def _available(
    name: str,
    value: float,
    formula: str,
    inputs: dict[str, float],
    components: dict[str, Any],
    interpretation: str,
    warnings: list[str] | None = None,
    unit: str = "score",
    note: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "validation_status": "available",
        "value": value,
        "unit": unit,
        "formula": formula,
        "inputs": inputs,
        "components": components,
        "interpretation": interpretation,
        "warnings": warnings or [],
        "missing_fields": [],
        "note": note or None,
    }


def _period_rows(payload: dict[str, Any]) -> list[dict[str, dict[str, Any]]]:
    financials = payload.get("financials")
    if not isinstance(financials, dict):
        raise ValueError("Financial Datasets response has no financials object.")
    collections = {
        "income": financials.get("income_statements", []),
        "balance": financials.get("balance_sheets", []),
        "cash_flow": financials.get("cash_flow_statements", []),
    }
    by_period: dict[str, dict[str, dict[str, Any]]] = {}
    for row_name, rows in collections.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("period") != "annual":
                continue
            period = str(row.get("report_period") or "")
            if period:
                by_period.setdefault(period, {})[row_name] = row
    complete = [
        {"period": {"report_period": period}, **rows}
        for period, rows in by_period.items()
        if all(name in rows for name in collections)
    ]
    complete.sort(key=lambda item: item["period"]["report_period"], reverse=True)
    return complete


def fetch_financials(ticker: str, api_key: str, limit: int = 3) -> dict[str, Any]:
    """Fetch one combined annual-financials response without logging the key."""
    if not api_key.strip():
        raise RuntimeError("FINANCIAL_DATASETS_API_KEY is not configured.")
    query = urlencode({"ticker": ticker.upper(), "period": "annual", "limit": limit})
    request = Request(
        f"{API_URL}?{query}",
        headers={
            "X-API-KEY": api_key.strip(),
            "Accept": "application/json",
            "User-Agent": "Devashish Batra batra44@purdue.edu",
        },
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Financial Datasets returned HTTP {response.status}.")
        return json.load(response)


def _piotroski(current: dict[str, dict[str, Any]], prior: dict[str, dict[str, Any]]) -> dict[str, Any]:
    requirements = [
        ("income", "net_income"), ("income", "gross_profit"), ("income", "revenue"),
        ("balance", "total_assets"), ("balance", "non_current_debt"),
        ("balance", "current_assets"), ("balance", "current_liabilities"),
        ("balance", "outstanding_shares"), ("cash_flow", "net_cash_flow_from_operations"),
    ]
    missing = _missing(current, requirements) + [f"prior.{item}" for item in _missing(prior, requirements[:-1])]
    if missing:
        return _unavailable("piotroski_f_score", "Nine binary financial-strength signals", missing)
    c_i, c_b, c_c = current["income"], current["balance"], current["cash_flow"]
    p_i, p_b = prior["income"], prior["balance"]
    ni, cfo, assets = _number(c_i, "net_income"), _number(c_c, "net_cash_flow_from_operations"), _number(c_b, "total_assets")
    ni_p, assets_p = _number(p_i, "net_income"), _number(p_b, "total_assets")
    assert None not in (ni, cfo, assets, ni_p, assets_p)
    roa = _safe_div(ni, assets)
    roa_p = _safe_div(ni_p, assets_p)
    cfo_assets = _safe_div(cfo, assets)
    leverage = _safe_div(_number(c_b, "non_current_debt"), assets)
    leverage_p = _safe_div(_number(p_b, "non_current_debt"), assets_p)
    current_ratio = _safe_div(_number(c_b, "current_assets"), _number(c_b, "current_liabilities"))
    current_ratio_p = _safe_div(_number(p_b, "current_assets"), _number(p_b, "current_liabilities"))
    margin = _safe_div(_number(c_i, "gross_profit"), _number(c_i, "revenue"))
    margin_p = _safe_div(_number(p_i, "gross_profit"), _number(p_i, "revenue"))
    turnover = _safe_div(_number(c_i, "revenue"), assets)
    turnover_p = _safe_div(_number(p_i, "revenue"), assets_p)
    components = {
        "f1_roa_positive": int(roa > 0),
        "f2_cfo_positive": int(cfo_assets > 0),
        "f3_roa_improving": int(roa > roa_p),
        "f4_accruals_quality": int(cfo_assets > roa),
        "f5_leverage_decreasing": int(leverage < leverage_p),
        "f6_liquidity_improving": int(current_ratio > current_ratio_p),
        "f7_no_dilution": int(_number(c_b, "outstanding_shares") <= _number(p_b, "outstanding_shares")),
        "f8_margin_improving": int(margin > margin_p),
        "f9_turnover_improving": int(turnover > turnover_p),
    }
    score = sum(components.values())
    interpretation = "Very strong" if score >= 8 else "Strong" if score == 7 else "Mixed" if score >= 4 else "Weak"
    inputs = {
        "current_net_income": ni,
        "current_operating_cash_flow": cfo,
        "current_total_assets": assets,
        "current_non_current_debt": _number(c_b, "non_current_debt"),
        "current_current_assets": _number(c_b, "current_assets"),
        "current_current_liabilities": _number(c_b, "current_liabilities"),
        "current_outstanding_shares": _number(c_b, "outstanding_shares"),
        "current_gross_profit": _number(c_i, "gross_profit"),
        "current_revenue": _number(c_i, "revenue"),
        "prior_net_income": ni_p,
        "prior_total_assets": assets_p,
        "prior_non_current_debt": _number(p_b, "non_current_debt"),
        "prior_current_assets": _number(p_b, "current_assets"),
        "prior_current_liabilities": _number(p_b, "current_liabilities"),
        "prior_outstanding_shares": _number(p_b, "outstanding_shares"),
        "prior_gross_profit": _number(p_i, "gross_profit"),
        "prior_revenue": _number(p_i, "revenue"),
    }
    return _available(
        "piotroski_f_score", score, "Sum of nine binary signals", inputs, components,
        f"{interpretation} financial-strength signal under the FAskills thresholds.", unit="points out of 9",
    )


def _altman(current: dict[str, dict[str, Any]], price: float) -> dict[str, dict[str, Any]]:
    requirements = [
        ("income", "ebit"), ("income", "revenue"), ("balance", "current_assets"),
        ("balance", "current_liabilities"), ("balance", "retained_earnings"),
        ("balance", "total_assets"), ("balance", "total_liabilities"),
        ("balance", "outstanding_shares"),
    ]
    missing = _missing(current, requirements)
    if not price or price <= 0:
        missing.append("documented_share_price")
    if missing:
        unavailable = _unavailable("altman_z_score", "Altman Z and Z-double-prime models", missing)
        return {"altman_z_manufacturing": unavailable, "altman_z_nonmanufacturing": dict(unavailable)}
    income, balance = current["income"], current["balance"]
    assets = _number(balance, "total_assets")
    liabilities = _number(balance, "total_liabilities")
    market_cap = price * _number(balance, "outstanding_shares")
    working_capital = _number(balance, "current_assets") - _number(balance, "current_liabilities")
    x1 = _safe_div(working_capital, assets)
    x2 = _safe_div(_number(balance, "retained_earnings"), assets)
    x3 = _safe_div(_number(income, "ebit"), assets)
    x4 = _safe_div(market_cap, liabilities)
    x5 = _safe_div(_number(income, "revenue"), assets)
    components = {"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5}
    manufacturing = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 0.999*x5
    nonmanufacturing = 6.56*x1 + 3.26*x2 + 6.72*x3 + 1.05*x4
    shared_inputs = {
        "share_price": price,
        "outstanding_shares": _number(balance, "outstanding_shares"),
        "market_cap": market_cap,
        "working_capital": working_capital,
        "retained_earnings": _number(balance, "retained_earnings"),
        "ebit": _number(income, "ebit"),
        "revenue": _number(income, "revenue"),
        "total_assets": assets,
        "total_liabilities": liabilities,
    }
    return {
        "altman_z_manufacturing": _available(
            "altman_z_manufacturing", round(manufacturing, 4),
            "1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.999*X5", shared_inputs, components,
            "Safe zone" if manufacturing > 2.99 else "Grey zone" if manufacturing > 1.81 else "Distress zone",
            note="Use only for a public manufacturing company.",
        ),
        "altman_z_nonmanufacturing": _available(
            "altman_z_nonmanufacturing", round(nonmanufacturing, 4),
            "6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4", shared_inputs, {key: components[key] for key in ("x1", "x2", "x3", "x4")},
            "Safe zone" if nonmanufacturing > 2.60 else "Grey zone" if nonmanufacturing > 1.10 else "Distress zone",
            note="Use only for a non-manufacturing company. The code does not guess the industry classification.",
        ),
    }


def _beneish(current: dict[str, dict[str, Any]], prior: dict[str, dict[str, Any]]) -> dict[str, Any]:
    requirements = [
        ("income", "revenue"), ("income", "gross_profit"),
        ("income", "selling_general_and_administrative_expenses"), ("income", "net_income"),
        ("balance", "trade_and_non_trade_receivables"), ("balance", "current_assets"),
        ("balance", "property_plant_and_equipment"), ("balance", "total_assets"),
        ("balance", "total_debt"), ("cash_flow", "depreciation_and_amortization"),
        ("cash_flow", "net_cash_flow_from_operations"),
    ]
    prior_requirements = [item for item in requirements if item not in {
        ("income", "net_income"), ("cash_flow", "net_cash_flow_from_operations")
    }]
    missing = _missing(current, requirements) + [f"prior.{item}" for item in _missing(prior, prior_requirements)]
    if missing:
        return _unavailable("beneish_m_score", "Eight-variable Beneish M-Score", missing)
    ci, cb, cc = current["income"], current["balance"], current["cash_flow"]
    pi, pb, pc = prior["income"], prior["balance"], prior["cash_flow"]
    dsri = _safe_div(_safe_div(_number(cb, "trade_and_non_trade_receivables"), _number(ci, "revenue")), _safe_div(_number(pb, "trade_and_non_trade_receivables"), _number(pi, "revenue")))
    gmi = _safe_div(_safe_div(_number(pi, "gross_profit"), _number(pi, "revenue")), _safe_div(_number(ci, "gross_profit"), _number(ci, "revenue")))
    aq = 1 - _safe_div(_number(cb, "current_assets") + _number(cb, "property_plant_and_equipment"), _number(cb, "total_assets"))
    aq_prior = 1 - _safe_div(_number(pb, "current_assets") + _number(pb, "property_plant_and_equipment"), _number(pb, "total_assets"))
    aqi = _safe_div(aq, aq_prior)
    sgi = _safe_div(_number(ci, "revenue"), _number(pi, "revenue"))
    dep_rate = _safe_div(_number(cc, "depreciation_and_amortization"), _number(cc, "depreciation_and_amortization") + _number(cb, "property_plant_and_equipment"))
    dep_rate_prior = _safe_div(_number(pc, "depreciation_and_amortization"), _number(pc, "depreciation_and_amortization") + _number(pb, "property_plant_and_equipment"))
    depi = _safe_div(dep_rate_prior, dep_rate)
    sgai = _safe_div(_safe_div(_number(ci, "selling_general_and_administrative_expenses"), _number(ci, "revenue")), _safe_div(_number(pi, "selling_general_and_administrative_expenses"), _number(pi, "revenue")))
    lvgi = _safe_div(_safe_div(_number(cb, "total_debt"), _number(cb, "total_assets")), _safe_div(_number(pb, "total_debt"), _number(pb, "total_assets")))
    tata = _safe_div(_number(ci, "net_income") - _number(cc, "net_cash_flow_from_operations"), _number(cb, "total_assets"))
    components = {"dsri": dsri, "gmi": gmi, "aqi": aqi, "sgi": sgi, "depi": depi, "sgai": sgai, "lvgi": lvgi, "tata": tata}
    score = -4.84 + 0.920*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi + 0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi
    warnings = [name.upper() for name, value, threshold in (("dsri", dsri, 1.05), ("gmi", gmi, 1.04), ("aqi", aqi, 1.0), ("depi", depi, 1.0), ("tata", tata, 0.05)) if value > threshold]
    interpretation = "Likely manipulation signal" if score > -1.78 else "Grey zone" if score > -2.22 else "Unlikely manipulation signal"
    inputs = {
        "current_receivables": _number(cb, "trade_and_non_trade_receivables"),
        "current_revenue": _number(ci, "revenue"),
        "current_gross_profit": _number(ci, "gross_profit"),
        "current_assets": _number(cb, "total_assets"),
        "current_current_assets": _number(cb, "current_assets"),
        "current_ppe": _number(cb, "property_plant_and_equipment"),
        "current_depreciation_and_amortization": _number(cc, "depreciation_and_amortization"),
        "current_sga": _number(ci, "selling_general_and_administrative_expenses"),
        "current_total_debt": _number(cb, "total_debt"),
        "current_net_income": _number(ci, "net_income"),
        "current_operating_cash_flow": _number(cc, "net_cash_flow_from_operations"),
        "prior_receivables": _number(pb, "trade_and_non_trade_receivables"),
        "prior_revenue": _number(pi, "revenue"),
        "prior_gross_profit": _number(pi, "gross_profit"),
        "prior_assets": _number(pb, "total_assets"),
        "prior_current_assets": _number(pb, "current_assets"),
        "prior_ppe": _number(pb, "property_plant_and_equipment"),
        "prior_depreciation_and_amortization": _number(pc, "depreciation_and_amortization"),
        "prior_sga": _number(pi, "selling_general_and_administrative_expenses"),
        "prior_total_debt": _number(pb, "total_debt"),
    }
    return _available(
        "beneish_m_score", round(score, 4),
        "-4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI",
        inputs, components, interpretation, warnings,
        note="This adaptation uses each period's own current-assets value. Missing inputs make the score unavailable.",
    )


def _owner_earnings(current: dict[str, dict[str, Any]], prior: dict[str, dict[str, Any]]) -> dict[str, Any]:
    requirements = [
        ("income", "net_income"), ("balance", "current_assets"),
        ("balance", "current_liabilities"), ("balance", "outstanding_shares"),
        ("cash_flow", "depreciation_and_amortization"), ("cash_flow", "capital_expenditure"),
    ]
    prior_requirements = [("balance", "current_assets"), ("balance", "current_liabilities")]
    missing = _missing(current, requirements) + [f"prior.{item}" for item in _missing(prior, prior_requirements)]
    if missing:
        return _unavailable("owner_earnings", "Net income + D&A - capex - increase in working capital", missing)
    ci, cb, cc, pb = current["income"], current["balance"], current["cash_flow"], prior["balance"]
    working_capital = _number(cb, "current_assets") - _number(cb, "current_liabilities")
    working_capital_prior = _number(pb, "current_assets") - _number(pb, "current_liabilities")
    change = working_capital - working_capital_prior
    capex = abs(_number(cc, "capital_expenditure"))
    value = _number(ci, "net_income") + _number(cc, "depreciation_and_amortization") - capex - change
    shares = _number(cb, "outstanding_shares")
    return _available(
        "owner_earnings", value, "Net income + D&A - capex - increase in working capital",
        {"net_income": _number(ci, "net_income"), "depreciation_and_amortization": _number(cc, "depreciation_and_amortization"), "capex": capex, "working_capital_change": change},
        {"per_share": _safe_div(value, shares)},
        "Positive owner earnings" if value > 0 else "Negative owner earnings", unit="currency units",
        note="Full capex is used as a conservative maintenance-capex proxy.",
    )


def _dupont(current: dict[str, dict[str, Any]]) -> dict[str, Any]:
    requirements = [
        ("income", "net_income"), ("income", "income_tax_expense"), ("income", "ebit"),
        ("income", "revenue"), ("balance", "total_assets"), ("balance", "shareholders_equity"),
    ]
    missing = _missing(current, requirements)
    if missing:
        return _unavailable("dupont_5_factor", "Tax burden * interest burden * EBIT margin * asset turnover * leverage", missing)
    income, balance = current["income"], current["balance"]
    net_income = _number(income, "net_income")
    ebt = net_income + _number(income, "income_tax_expense")
    ebit = _number(income, "ebit")
    revenue = _number(income, "revenue")
    assets = _number(balance, "total_assets")
    equity = _number(balance, "shareholders_equity")
    components = {
        "tax_burden": _safe_div(net_income, ebt),
        "interest_burden": _safe_div(ebt, ebit),
        "ebit_margin": _safe_div(ebit, revenue),
        "asset_turnover": _safe_div(revenue, assets),
        "leverage": _safe_div(assets, equity),
    }
    value = math.prod(components.values())
    return _available(
        "dupont_5_factor", value, "Tax burden * interest burden * EBIT margin * asset turnover * leverage",
        {
            "net_income": net_income,
            "income_tax_expense": _number(income, "income_tax_expense"),
            "derived_earnings_before_tax": ebt,
            "ebit": ebit,
            "revenue": revenue,
            "total_assets": assets,
            "shareholders_equity": equity,
        }, components, f"Decomposed ROE is {value:.2%}.", unit="ratio",
        note="Earnings before tax is derived as net income plus income-tax expense because the combined endpoint does not supply an EBT field.",
    )


def _quality_metrics(current: dict[str, dict[str, Any]], prior: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    sloan_req = [("income", "net_income"), ("balance", "total_assets"), ("cash_flow", "net_cash_flow_from_operations")]
    sloan_missing = _missing(current, sloan_req) + [f"prior.{item}" for item in _missing(prior, [("balance", "total_assets")])]
    if sloan_missing:
        results["sloan_accrual_ratio"] = _unavailable("sloan_accrual_ratio", "(Net income - operating cash flow) / average total assets", sloan_missing)
    else:
        ni = _number(current["income"], "net_income")
        cfo = _number(current["cash_flow"], "net_cash_flow_from_operations")
        avg_assets = (_number(current["balance"], "total_assets") + _number(prior["balance"], "total_assets")) / 2
        value = _safe_div(ni - cfo, avg_assets)
        results["sloan_accrual_ratio"] = _available(
            "sloan_accrual_ratio", value, "(Net income - operating cash flow) / average total assets",
            {"net_income": ni, "operating_cash_flow": cfo, "average_assets": avg_assets}, {},
            "FAskills safe zone" if -0.10 <= value <= 0.10 else "Outside the FAskills safe zone", unit="ratio",
        )
    gp_missing = _missing(current, [("income", "gross_profit"), ("balance", "total_assets")])
    if gp_missing:
        results["gross_profitability"] = _unavailable("gross_profitability", "Gross profit / total assets", gp_missing)
    else:
        value = _safe_div(_number(current["income"], "gross_profit"), _number(current["balance"], "total_assets"))
        results["gross_profitability"] = _available(
            "gross_profitability", value, "Gross profit / total assets",
            {"gross_profit": _number(current["income"], "gross_profit"), "total_assets": _number(current["balance"], "total_assets")}, {},
            "Gross profit generated per unit of year-end assets.", unit="ratio",
        )
    fcf_missing = _missing(current, [("income", "ebit"), ("income", "net_income"), ("cash_flow", "depreciation_and_amortization"), ("cash_flow", "free_cash_flow")])
    if fcf_missing:
        results["fcf_conversion"] = _unavailable("fcf_conversion", "Free cash flow / derived EBITDA", fcf_missing)
    else:
        fcf = _number(current["cash_flow"], "free_cash_flow")
        ebitda = _number(current["income"], "ebit") + _number(current["cash_flow"], "depreciation_and_amortization")
        value = _safe_div(fcf, ebitda)
        results["fcf_conversion"] = _available(
            "fcf_conversion", value, "Free cash flow / (EBIT + D&A)",
            {"free_cash_flow": fcf, "derived_ebitda": ebitda},
            {"fcf_to_net_income": _safe_div(fcf, _number(current["income"], "net_income"))},
            "Strong under the FAskills threshold" if value >= 0.80 else "Below the FAskills 80% threshold", unit="ratio",
        )
    return results


def calculate_metrics(payload: dict[str, Any], price: float) -> dict[str, Any]:
    periods = _period_rows(payload)
    if len(periods) < 2:
        raise ValueError("At least two complete annual periods are required.")
    current, prior = periods[0], periods[1]
    metrics: dict[str, Any] = {
        "piotroski_f_score": _piotroski(current, prior),
        **_altman(current, price),
        "beneish_m_score": _beneish(current, prior),
        "owner_earnings": _owner_earnings(current, prior),
        "dupont_5_factor": _dupont(current),
        **_quality_metrics(current, prior),
    }
    return {
        "current_period": current["period"]["report_period"],
        "prior_period": prior["period"]["report_period"],
        "current_accession": current["income"].get("accession_number"),
        "prior_accession": prior["income"].get("accession_number"),
        "currency": current["income"].get("currency"),
        "metrics": metrics,
    }


def _sec_current(facts: dict[str, Any], concept: str) -> tuple[float | None, str | None]:
    current = facts.get("concepts", {}).get(concept, {}).get("current", {})
    value = current.get("value")
    return (float(value), current.get("period_end")) if value is not None else (None, current.get("period_end"))


def crosscheck_with_sec(payload: dict[str, Any], facts: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    current = _period_rows(payload)[0]
    api_values = {
        "total_revenue": _number(current["income"], "revenue"),
        "operating_income": _number(current["income"], "operating_income"),
        "net_income": _number(current["income"], "net_income"),
        "diluted_eps": _number(current["income"], "earnings_per_share_diluted"),
    }
    checks: dict[str, Any] = {}
    for concept, api_value in api_values.items():
        sec_value, sec_period = _sec_current(facts, concept)
        tolerance = 0.005 if concept == "diluted_eps" else 0.5
        checks[concept] = {
            "financialdatasets_value": api_value,
            "sec_value": sec_value,
            "sec_period_end": sec_period,
            "matches": api_value is not None and sec_value is not None and abs(api_value - sec_value) <= tolerance,
        }
    expected_accession = manifest.get("filings", {}).get("10-k", {}).get("accession_number")
    expected_period = manifest.get("filings", {}).get("10-k", {}).get("reporting_period")
    actual_accession = current["income"].get("accession_number")
    actual_period = current["period"]["report_period"]
    accession_matches = actual_accession == expected_accession
    period_matches = actual_period == expected_period
    approved = accession_matches and period_matches and all(item["matches"] for item in checks.values())
    return {
        "status": "approved" if approved else "failed",
        "accession_matches": accession_matches,
        "period_matches": period_matches,
        "expected_accession": expected_accession,
        "financialdatasets_accession": actual_accession,
        "expected_period": expected_period,
        "financialdatasets_period": actual_period,
        "checks": checks,
    }


def enrich_run_folder(run_folder: Path, ticker: str, price: float, repository_root: Path) -> Path:
    """Fetch, calculate, cross-check, and save the optional FAskills sidecar."""
    load_dotenv(repository_root / ".env", override=False)
    api_key = (os.getenv("FINANCIAL_DATASETS_API_KEY") or "").strip()
    payload = fetch_financials(ticker, api_key)
    facts = json.loads((run_folder / "facts.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))
    calculation = calculate_metrics(payload, price)
    crosscheck = crosscheck_with_sec(payload, facts, manifest)
    raw_path = run_folder / "faskills_financialdatasets.json"
    raw_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output = {
        "integration_version": "1.0.0",
        "generated_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker.upper(),
        "provider": PROVIDER,
        "endpoint": API_URL,
        "adapted_from": ADAPTATION_SOURCE,
        "course_boundary": {
            "guru_personas_enabled": False,
            "nine_analytical_lenses_enabled": True,
            "automatic_price_targets_enabled": False,
            "verifier_bypass_enabled": False,
            "report_use_allowed": crosscheck["status"] == "approved",
        },
        "source_periods": {key: calculation[key] for key in ("current_period", "prior_period", "current_accession", "prior_accession", "currency")},
        "sec_crosscheck": crosscheck,
        "metrics": calculation["metrics"],
    }
    output_path = run_folder / "faskills_metrics.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["faskills_extension"] = {
        "enabled": True,
        "status": crosscheck["status"],
        "source": ADAPTATION_SOURCE,
        "provider": PROVIDER,
        "metrics_file": output_path.name,
        "local_raw_file": raw_path.name,
    }
    manifest["output_filenames"] = sorted(set(manifest.get("output_filenames", [])) | {output_path.name})
    (run_folder / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a course-safe FAskills metrics sidecar.")
    parser.add_argument("ticker")
    parser.add_argument("--run-folder", type=Path, required=True)
    parser.add_argument("--price", type=float, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    repository_root = Path(__file__).resolve().parents[3]
    path = enrich_run_folder(args.run_folder.resolve(), args.ticker, args.price, repository_root)
    print(f"FAskills metrics saved: {path}")


if __name__ == "__main__":
    main()
