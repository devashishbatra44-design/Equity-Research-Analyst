"""Build deterministic numeric results for one saved Week 4 worksheet run."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from .investor_worksheet import (
    liquidity_check,
    liquidity_check_from_median,
    owner_cash_flow,
    value_range,
)


def _decimal(payload: dict[str, Any], key: str) -> Decimal:
    return Decimal(str(payload[key]))


def calculate(payload: dict[str, Any], reader: dict[str, Any]) -> dict[str, Any]:
    tax_rate = _decimal(payload, "operating_tax_rate")
    one_time_cost = _decimal(payload, "one_time_cost")
    after_tax_adjustment = one_time_cost * (Decimal("1") - tax_rate)
    reported_earnings = _decimal(payload, "reported_after_tax_earnings")
    course_cash_flow = owner_cash_flow(
        reported_earnings,
        _decimal(payload, "depreciation"),
        _decimal(payload, "capital_expenditures"),
    )
    adjusted_earnings = reported_earnings + after_tax_adjustment
    adjusted_cash_flow = owner_cash_flow(
        adjusted_earnings,
        _decimal(payload, "depreciation"),
        _decimal(payload, "capital_expenditures"),
    )
    quarterly_interest = _decimal(payload, "post_spin_quarterly_interest_expense")
    annualization_periods = _decimal(payload, "interest_annualization_periods")
    annualized_interest = quarterly_interest * annualization_periods
    after_tax_interest = annualized_interest * (Decimal("1") - tax_rate)
    valuation_cash_flow = adjusted_cash_flow.value - after_tax_interest

    shares = _decimal(payload, "diluted_shares_millions")
    close = _decimal(payload, "official_close")
    primary = value_range(
        valuation_cash_flow,
        method="multiple",
        low_input=_decimal(payload, "low_multiple"),
        mid_input=_decimal(payload, "mid_multiple"),
        price=close * shares,
    )
    high_value = valuation_cash_flow * _decimal(payload, "high_multiple")
    stress_value = valuation_cash_flow * _decimal(payload, "stress_multiple")

    pairs = [
        (Decimal(str(record["close"])), Decimal(str(record["volume"])))
        for record in reader.get("records", [])
        if record.get("close") not in (None, "") and record.get("volume") not in (None, "")
    ]
    intended_purchase_size = _decimal(payload, "intended_purchase_size")
    minimum_ratio = Decimal("1") / _decimal(payload, "maximum_purchase_fraction")
    if reader.get("median_daily_dollar_volume") not in (None, ""):
        liquidity = liquidity_check_from_median(
            Decimal(str(reader["median_daily_dollar_volume"])),
            intended_purchase_size=intended_purchase_size,
            minimum_ratio=minimum_ratio,
        )
    else:
        liquidity = liquidity_check(
            pairs,
            intended_purchase_size=intended_purchase_size,
            minimum_ratio=minimum_ratio,
        )

    low_per_share = primary.low_value / shares
    mid_per_share = primary.mid_value / shares
    valuation_gap = low_per_share - close
    if liquidity.status == "not computed":
        conviction = "not computed"
    elif valuation_gap >= 0 and liquidity.status == "passes":
        conviction = "high"
    else:
        conviction = "low"

    purchase_size = _decimal(payload, "intended_purchase_size")
    maximum_fraction = _decimal(payload, "maximum_purchase_fraction")
    purchase_fraction = (
        purchase_size / liquidity.median_daily_dollar_volume
        if liquidity.median_daily_dollar_volume is not None
        and liquidity.median_daily_dollar_volume != 0
        else None
    )

    return {
        "reported_after_tax_earnings_usd_millions": str(reported_earnings),
        "one_time_cost_usd_millions": str(one_time_cost),
        "operating_tax_rate": str(tax_rate),
        "after_tax_one_time_adjustment_usd_millions": str(after_tax_adjustment),
        "adjusted_after_tax_earnings_usd_millions": str(adjusted_earnings),
        "depreciation_usd_millions": str(course_cash_flow.depreciation),
        "capital_expenditures_usd_millions": str(course_cash_flow.capital_expenditures),
        "course_owner_cash_flow_usd_millions": str(course_cash_flow.value),
        "adjusted_owner_cash_flow_before_new_debt_interest_usd_millions": str(adjusted_cash_flow.value),
        "post_spin_quarterly_interest_expense_usd_millions": str(quarterly_interest),
        "interest_annualization_periods": str(annualization_periods),
        "annualized_post_spin_interest_expense_usd_millions": str(annualized_interest),
        "after_tax_annualized_post_spin_interest_expense_usd_millions": str(after_tax_interest),
        "valuation_owner_cash_flow_usd_millions": str(valuation_cash_flow),
        "owner_cash_flow_usd_millions": str(course_cash_flow.value),
        "diluted_shares_millions": str(shares),
        "official_close_usd_per_share": str(close),
        "low_multiple": str(primary.low_input),
        "mid_multiple": str(primary.mid_input),
        "high_multiple": str(_decimal(payload, "high_multiple")),
        "stress_multiple": str(_decimal(payload, "stress_multiple")),
        "low_equity_value_usd_millions": str(primary.low_value),
        "mid_equity_value_usd_millions": str(primary.mid_value),
        "high_equity_value_usd_millions": str(high_value),
        "stress_equity_value_usd_millions": str(stress_value),
        "low_value_usd_per_share": str(low_per_share),
        "mid_value_usd_per_share": str(mid_per_share),
        "high_value_usd_per_share": str(high_value / shares),
        "stress_value_usd_per_share": str(stress_value / shares),
        "valuation_gap_usd_per_share": str(valuation_gap),
        "median_daily_dollar_volume_usd": (
            str(liquidity.median_daily_dollar_volume)
            if liquidity.median_daily_dollar_volume is not None
            else None
        ),
        "intended_purchase_size_usd": str(purchase_size),
        "maximum_purchase_fraction": str(maximum_fraction),
        "required_median_daily_dollar_volume_usd": format(purchase_size / maximum_fraction, "f"),
        "median_daily_dollar_volume_to_purchase_ratio": (
            str(liquidity.ratio) if liquidity.ratio is not None else None
        ),
        "purchase_fraction_of_median_daily_dollar_volume": (
            str(purchase_fraction) if purchase_fraction is not None else None
        ),
        "purchase_percent_of_median_daily_dollar_volume": (
            str(purchase_fraction * Decimal("100")) if purchase_fraction is not None else None
        ),
        "liquidity_status": liquidity.status,
        "conviction": conviction,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--reader", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.inputs.read_text(encoding="utf-8"))
    reader = json.loads(args.reader.read_text(encoding="utf-8"))
    result = calculate(payload, reader)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
