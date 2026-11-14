"""Deterministic Week 4 spinoff registry, scoring, and report helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
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
    """Return the first supplied regular close after the distribution date."""

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
    if entry.record_date is None or entry.distribution_date is None:
        return RankedEntry(entry, stage, (), None, price, "required date missing")
    if not entry.is_spinoff:
        return RankedEntry(entry, stage, (), None, price, entry.drop_reason or "not a spinoff")

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
    price_date: date | None,
    index_date: date,
) -> str:
    """Render the required ranked, watch, dropped, and data-limit sections."""

    first = (
        f"Run date: {run_date.isoformat()} | Price date: "
        f"{price_date.isoformat() if price_date else 'not available'} | Index date: {index_date.isoformat()}"
    )
    ranked = sorted(
        (result for result in results if result.total_points is not None),
        key=lambda result: (-result.total_points, result.entry.name),
    )
    watch = [
        result
        for result in results
        if result.total_points is None and result.entry.is_spinoff
    ]
    dropped = [result for result in results if not result.entry.is_spinoff]

    lines = [first, "", "## Ranked"]
    if ranked:
        for result in ranked:
            lines.append(f"- {result.entry.name}: {result.total_points} points; stage: {result.stage.value}")
            for point in result.factor_points:
                value = "missing" if point.matched is None else str(point.matched).lower()
                lines.append(f"  - {point.factor_id}: {value}; {point.points} points")
    else:
        lines.append("- None.")

    lines.extend(["", "## Watch"])
    lines.extend(
        [f"- {result.entry.name}: {result.unranked_reason}." for result in watch] or ["- None."]
    )
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
        [f"- {result.entry.name}: {result.unranked_reason}." for result in limits]
        or ["- None."]
    )
    lines.extend(["", FINAL_LINE])
    return "\n".join(lines) + "\n"
