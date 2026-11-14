"""Deterministic Week 4 investor worksheet calculations and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Sequence


@dataclass(frozen=True)
class FactLine:
    fact_id: str
    label: str
    value: Decimal | str | None
    unit: str
    period: str
    form: str
    accession: str
    section: str
    source_url: str
    fact_class: str

    def __post_init__(self) -> None:
        if self.fact_class not in {"historical", "pro forma", "post-spin", "transaction"}:
            raise ValueError(f"Unsupported fact class: {self.fact_class}")


@dataclass(frozen=True)
class OwnerCashFlow:
    after_tax_earnings: Decimal
    depreciation: Decimal
    capital_expenditures: Decimal
    value: Decimal


@dataclass(frozen=True)
class ValueRange:
    method: str
    low_input: Decimal
    mid_input: Decimal
    low_value: Decimal
    mid_value: Decimal
    price: Decimal | None
    price_vs_low: str


@dataclass(frozen=True)
class LiquidityResult:
    median_daily_dollar_volume: Decimal | None
    intended_purchase_size: Decimal
    ratio: Decimal | None
    status: str


def owner_cash_flow(
    after_tax_earnings: Decimal,
    depreciation: Decimal,
    capital_expenditures: Decimal,
) -> OwnerCashFlow:
    value = after_tax_earnings + depreciation - capital_expenditures
    return OwnerCashFlow(after_tax_earnings, depreciation, capital_expenditures, value)


def value_range(
    cash_flow: Decimal,
    *,
    method: str,
    low_input: Decimal,
    mid_input: Decimal,
    price: Decimal | None,
) -> ValueRange:
    """Apply human-supplied capitalization rates or multiples."""

    if low_input <= 0 or mid_input <= 0:
        raise ValueError("Value inputs must be positive.")
    if method == "capitalization rate":
        low_value = cash_flow / low_input
        mid_value = cash_flow / mid_input
    elif method == "multiple":
        low_value = cash_flow * low_input
        mid_value = cash_flow * mid_input
    else:
        raise ValueError("Method must be capitalization rate or multiple.")
    if low_value > mid_value:
        raise ValueError("The human inputs produce a low value above the mid value.")
    comparison = "not computed" if price is None else ("more" if low_value > price else "less")
    return ValueRange(method, low_input, mid_input, low_value, mid_value, price, comparison)


def liquidity_check(
    daily_close_and_volume: Sequence[tuple[Decimal, Decimal]],
    *,
    intended_purchase_size: Decimal,
    minimum_ratio: Decimal,
) -> LiquidityResult:
    if intended_purchase_size <= 0 or minimum_ratio <= 0:
        raise ValueError("Client size and minimum ratio must be positive.")
    values = [close * volume for close, volume in daily_close_and_volume if close > 0 and volume >= 0]
    if not values:
        return LiquidityResult(None, intended_purchase_size, None, "not computed")
    median_value = Decimal(str(median(values)))
    ratio = median_value / intended_purchase_size
    return LiquidityResult(median_value, intended_purchase_size, ratio, "passes" if ratio >= minimum_ratio else "fails")


def render_fact(fact: FactLine) -> str:
    value = "not known" if fact.value is None else str(fact.value)
    unit = f" {fact.unit}" if fact.unit else ""
    return (
        f"{fact.label}: {value}{unit} | class: {fact.fact_class} | period: {fact.period} | "
        f"source: {fact.form} {fact.accession}, {fact.section}, {fact.source_url}"
    )


def render_owner_cash_flow(result: OwnerCashFlow, *, unit: str, period: str, citation: str) -> str:
    return (
        f"Owner cash flow: {result.after_tax_earnings} + {result.depreciation} - "
        f"{result.capital_expenditures} = {result.value} {unit} | period: {period} | source: {citation}"
    )
