"""Deterministic Week 4 spinoff registry, scoring, and report helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Sequence

from .closes_reader import CloseRecord


FINAL_LINE = "screens, not recommendations"


class Stage(StrEnum):
    REGISTERED = "registered"
    LISTING_APPROVED = "listing approved"
    TRADING = "trading"
    IN_WINDOW = "in window"
    PAST = "past"


@dataclass(frozen=True)
class FilingReference:
    form: str
    accession: str
    url: str
    section: str


@dataclass(frozen=True)
class RegistryEntry:
    name: str
    parent: str
    child_cik: str
    parent_cik: str
    ratio: str | None
    record_date: date | None
    distribution_date: date | None
    form10: FilingReference
    distribution_8k: FilingReference | None
    listing_approved: bool = False
    regular_trading: bool = False
    is_spinoff: bool = True
    drop_reason: str | None = None
    facts: Mapping[str, bool | int | Decimal | None] = field(default_factory=dict)


@dataclass(frozen=True)
class FactorSpec:
    factor_id: str
    direction: str
    weight: Decimal
    missing_rule: str

    def __post_init__(self) -> None:
        if self.direction not in {"higher", "lower", "yes", "no"}:
            raise ValueError(f"Unsupported factor direction: {self.direction}")
        if self.weight < 0:
            raise ValueError("Factor weight must not be negative.")
        if self.missing_rule not in {"zero", "unranked"}:
            raise ValueError("Missing-data rule must be zero or unranked.")


@dataclass(frozen=True)
class HumanFactorConfig:
    window_start: date
    window_end: date
    index_date: date
    post_distribution_window_days: int
    factors: tuple[FactorSpec, ...]


@dataclass(frozen=True)
class Form4Transaction:
    transaction_date: date
    transaction_code: str
    is_officer: bool = False
    is_director: bool = False


@dataclass(frozen=True)
class FactorPoint:
    factor_id: str
    matched: bool | None
    points: Decimal


@dataclass(frozen=True)
class RankedEntry:
    entry: RegistryEntry
    stage: Stage
    factor_points: tuple[FactorPoint, ...]
    total_points: Decimal | None
    price: CloseRecord | None
    unranked_reason: str | None


_WRITTEN_DATE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+(\d{4})"
)


def _read_labeled_date(lines: Sequence[str], label: str) -> date:
    line = next((item for item in lines if item.startswith(label)), None)
    if line is None:
        raise ValueError(f"Missing human-factor date: {label}")
    match = _WRITTEN_DATE.search(line)
    if match is None:
        raise ValueError(f"Invalid human-factor date: {label}")
    return date.fromisoformat(
        f"{match.group(3)}-{datetime.strptime(match.group(1), '%B').month:02d}-{int(match.group(2)):02d}"
    )


def parse_human_factor_text(text: str) -> HumanFactorConfig:
    """Read the human-frozen window and factor settings from Markdown."""

    lines = text.splitlines()
    status = next((line for line in lines if line.startswith("Status:")), "")
    if "frozen" not in status.lower():
        raise ValueError("Human factors must be frozen before a seeker run.")

    window_start = _read_labeled_date(lines, "- Distribution start date:")
    window_end = _read_labeled_date(lines, "- Distribution end date or age limit:")
    index_date = _read_labeled_date(lines, "- Index date:")
    window_days_line = next(
        (item for item in lines if item.startswith("- Post-distribution window length:")),
        None,
    )
    if window_days_line is None:
        raise ValueError("Missing post-distribution window length.")
    window_days_match = re.search(r"(\d+)\s+calendar days", window_days_line)
    if window_days_match is None:
        raise ValueError("Invalid post-distribution window length.")
    post_distribution_window_days = int(window_days_match.group(1))
    if post_distribution_window_days <= 0:
        raise ValueError("Post-distribution window length must be positive.")
    if window_start > window_end:
        raise ValueError("Distribution start date must not follow the end date.")
    if not window_start <= index_date <= window_end:
        raise ValueError("Index date must be inside the distribution window.")

    factors: list[FactorSpec] = []
    for line in lines:
        if not re.match(r"^\|\s*F\d+\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            raise ValueError(f"Invalid human-factor row: {line}")
        factor_id, description, direction, weight, missing_rule, reason = cells
        if not description or not reason:
            raise ValueError(f"Factor {factor_id} requires a rule and a human reason.")
        factors.append(FactorSpec(factor_id, direction, Decimal(weight), missing_rule))
    if not factors:
        raise ValueError("No frozen factors were found.")
    return HumanFactorConfig(
        window_start,
        window_end,
        index_date,
        post_distribution_window_days,
        tuple(factors),
    )


def parse_human_factors(path: Path) -> HumanFactorConfig:
    """Read a UTF-8 human-factor Markdown file."""

    return parse_human_factor_text(path.read_text(encoding="utf-8"))


def child_market_cap_is_small(
    child_market_cap: Decimal | None,
    parent_market_cap: Decimal | None,
    *,
    maximum_ratio: Decimal = Decimal("0.10"),
) -> bool | None:
    """Apply frozen F1. Values must use the same currency and price date."""

    if child_market_cap is None or parent_market_cap is None:
        return None
    if child_market_cap < 0 or parent_market_cap <= 0 or maximum_ratio < 0:
        raise ValueError("Market capitalizations and the F1 threshold must be valid.")
    return child_market_cap / parent_market_cap <= maximum_ratio


def child_parent_market_cap_ratio_from_distribution(
    distributed_child_shares_per_parent_share: Decimal | None,
    fraction_of_child_distributed: Decimal | None,
    child_close: Decimal | None,
    parent_close: Decimal | None,
) -> Decimal | None:
    """Derive the same-date child/parent market-cap ratio from spin terms."""

    values = (
        distributed_child_shares_per_parent_share,
        fraction_of_child_distributed,
        child_close,
        parent_close,
    )
    if any(value is None for value in values):
        return None
    assert distributed_child_shares_per_parent_share is not None
    assert fraction_of_child_distributed is not None
    assert child_close is not None
    assert parent_close is not None
    if (
        distributed_child_shares_per_parent_share < 0
        or not Decimal("0") < fraction_of_child_distributed <= Decimal("1")
        or child_close <= 0
        or parent_close <= 0
    ):
        raise ValueError("Distribution terms and regular closes must be valid.")
    return (
        distributed_child_shares_per_parent_share
        / fraction_of_child_distributed
        * child_close
        / parent_close
    )


def no_debt_funded_cash_payment(amount: Decimal | None) -> bool | None:
    """Apply frozen F2 to the filing-stated debt-funded parent payment."""

    if amount is None:
        return None
    if amount < 0:
        raise ValueError("Debt-funded cash payment must not be negative.")
    return amount == 0


def has_qualifying_insider_purchase(
    transactions: Sequence[Form4Transaction] | None,
    *,
    distribution_date: date | None,
    index_date: date,
) -> bool | None:
    """Apply frozen F3 without using a transaction after the index date."""

    if transactions is None or distribution_date is None or index_date < distribution_date:
        return None
    last_eligible_date = min(distribution_date + timedelta(days=90), index_date)
    return any(
        distribution_date < transaction.transaction_date <= last_eligible_date
        and transaction.transaction_code.upper() == "P"
        and (transaction.is_officer or transaction.is_director)
        for transaction in transactions
    )


def classify_stage(
    entry: RegistryEntry,
    *,
    run_date: date,
    window_start: date,
    window_end: date,
) -> Stage:
    """Classify a registry entry without inferring a missing date."""

    distributed = entry.distribution_date is not None and entry.distribution_date <= run_date
    if entry.regular_trading:
        if distributed and window_start <= entry.distribution_date <= window_end:
            return Stage.IN_WINDOW
        if distributed and entry.distribution_date < window_start:
            return Stage.PAST
        return Stage.TRADING
    if entry.listing_approved:
        return Stage.LISTING_APPROVED
    return Stage.REGISTERED


def first_regular_close_after_distribution(
    distribution_date: date | None,
    closes: Sequence[CloseRecord],
) -> CloseRecord | None:
    """Return the first supplied regular close strictly after distribution."""

    if distribution_date is None:
        return None
    eligible = sorted(record for record in closes if record.pricing_date > distribution_date)
    return eligible[0] if eligible else None


def score_entry(
    entry: RegistryEntry,
    factors: Sequence[FactorSpec],
    *,
    run_date: date,
    window_start: date,
    window_end: date,
    closes: Sequence[CloseRecord] = (),
) -> RankedEntry:
    """Score human-defined factor matches supplied by deterministic code.

    ``entry.facts`` must contain booleans produced from the frozen human rules.
    This function does not choose factors or thresholds.
    """

    stage = classify_stage(entry, run_date=run_date, window_start=window_start, window_end=window_end)
    price = first_regular_close_after_distribution(entry.distribution_date, closes)
    if not entry.is_spinoff:
        return RankedEntry(entry, stage, (), None, price, entry.drop_reason or "not a spinoff")
    if entry.record_date is None or entry.distribution_date is None:
        return RankedEntry(entry, stage, (), None, price, "required date missing")

    points: list[FactorPoint] = []
    unranked_reason: str | None = None
    for factor in factors:
        raw = entry.facts.get(factor.factor_id)
        matched = raw if isinstance(raw, bool) else None
        if matched is None and factor.missing_rule == "unranked":
            unranked_reason = f"factor {factor.factor_id} missing"
        points.append(
            FactorPoint(
                factor_id=factor.factor_id,
                matched=matched,
                points=factor.weight if matched is True else Decimal("0"),
            )
        )
    total = None if unranked_reason else sum((point.points for point in points), Decimal("0"))
    return RankedEntry(entry, stage, tuple(points), total, price, unranked_reason)


def render_report(
    results: Sequence[RankedEntry],
    *,
    run_date: date,
    price_date: date | str | None,
    index_date: date,
    post_distribution_window_days: int = 365,
    run_time: datetime | str | None = None,
) -> str:
    """Render the required ranked, watch, dropped, and data-limit sections."""

    if isinstance(price_date, date):
        price_date_text = price_date.isoformat()
    else:
        price_date_text = price_date or "not available"
    first = (
        f"Run date: {run_date.isoformat()} | Price date: "
        f"{price_date_text} | Index date: {index_date.isoformat()}"
    )
    if run_time is not None:
        run_time_text = run_time.isoformat() if isinstance(run_time, datetime) else str(run_time)
        first += f" | Run time: {run_time_text}"
    ranked = sorted(
        (result for result in results if result.total_points is not None),
        key=lambda result: (-result.total_points, result.entry.name),
    )
    ranked_unranked = sorted(
        (
            result
            for result in results
            if result.total_points is None
            and result.entry.is_spinoff
            and result.stage in {Stage.TRADING, Stage.IN_WINDOW, Stage.PAST}
        ),
        key=lambda result: result.entry.name,
    )
    watch = [
        result
        for result in results
        if result.total_points is None
        and result.entry.is_spinoff
        and result.stage in {Stage.REGISTERED, Stage.LISTING_APPROVED}
    ]
    dropped = [result for result in results if not result.entry.is_spinoff]

    lines = [first, "", "## Ranked"]
    if ranked or ranked_unranked:
        for result in ranked:
            point_label = "point" if result.total_points == Decimal("1") else "points"
            lines.append(
                _report_row(
                    result,
                    points=f"{result.total_points} {point_label}",
                    post_distribution_window_days=post_distribution_window_days,
                )
            )
            for point in result.factor_points:
                value = "missing" if point.matched is None else str(point.matched).lower()
                point_label = "point" if point.points == Decimal("1") else "points"
                lines.append(f"  - {point.factor_id}: {value}; {point.points} {point_label}")
        for result in ranked_unranked:
            lines.append(
                _report_row(
                    result,
                    points=f"unranked: {(result.unranked_reason or '').rstrip('.')}",
                    post_distribution_window_days=post_distribution_window_days,
                )
            )
            for point in result.factor_points:
                value = "missing" if point.matched is None else str(point.matched).lower()
                point_label = "point" if point.points == Decimal("1") else "points"
                lines.append(f"  - {point.factor_id}: {value}; {point.points} {point_label}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Watch"])
    if watch:
        for result in watch:
            lines.append(
                _report_row(
                    result,
                    points=f"unranked: {(result.unranked_reason or '').rstrip('.')}",
                    post_distribution_window_days=post_distribution_window_days,
                )
            )
            for point in result.factor_points:
                value = "missing" if point.matched is None else str(point.matched).lower()
                point_label = "point" if point.points == Decimal("1") else "points"
                lines.append(f"  - {point.factor_id}: {value}; {point.points} {point_label}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Dropped"])
    lines.extend(
        [
            f"- {result.entry.name}: {result.unranked_reason}; "
            f"{result.entry.form10.form} {result.entry.form10.accession}, {result.entry.form10.section}."
            for result in dropped
        ]
        or ["- None."]
    )
    lines.extend(["", "## Data limits"])
    limits = [result for result in results if result.unranked_reason and result.entry.is_spinoff]
    lines.extend(
        [f"- {result.entry.name}: {result.unranked_reason.rstrip('.')}." for result in limits]
        or ["- None."]
    )
    lines.extend(["", FINAL_LINE])
    return "\n".join(lines) + "\n"


def _report_row(
    result: RankedEntry,
    *,
    points: str,
    post_distribution_window_days: int,
) -> str:
    """Render the course-required per-name facts without estimating blanks."""

    distributed = result.entry.distribution_date
    distribution_text = distributed.isoformat() if distributed else "not available"
    window_end = distributed + timedelta(days=post_distribution_window_days) if distributed else None
    window_end_text = window_end.isoformat() if window_end else "not available"
    if result.price is None:
        price_text = "price not available"
    else:
        price_text = (
            f"{result.price.close} {result.price.currency} "
            f"on {result.price.pricing_date.isoformat()}"
        )
    return (
        f"- {result.entry.name} | parent: {result.entry.parent or 'not available'} | "
        f"distributed: {distribution_text} | window ends: {window_end_text} | "
        f"{price_text} | {points}; stage: {result.stage.value}"
    )
