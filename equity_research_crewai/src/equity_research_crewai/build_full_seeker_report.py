"""Build the complete Week 4 seeker report from frozen, saved audit artifacts."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from .closes_reader import CloseRecord
from .spinoff_seeker import (
    FilingReference,
    RankedEntry,
    RegistryEntry,
    parse_human_factors,
    render_report,
    score_entry,
)


def _read_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected a JSON object in {path}.")
    return value


def _result_map(payload: Mapping[str, Any], label: str) -> dict[str, Mapping[str, Any]]:
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise ValueError(f"{label} has no results list.")
    mapped: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not str(row.get("child", "")).strip():
            raise ValueError(f"{label} has an invalid child row.")
        child = str(row["child"])
        if child in mapped:
            raise ValueError(f"{label} has duplicate child: {child}.")
        mapped[child] = row
    return mapped


def _date(value: object | None) -> date | None:
    return date.fromisoformat(str(value)) if value else None


def _accession_from_url(url: str) -> str:
    match = re.search(r"/(\d{10}-?\d{2}-?\d{6})/", url)
    return match.group(1) if match else "not available"


def build_results(
    registry: Mapping[str, Any],
    f1_payload: Mapping[str, Any],
    f2_payload: Mapping[str, Any],
    f3_payload: Mapping[str, Any],
    human_factors_path: Path,
    form10_screen: Mapping[str, Any] | None = None,
    *,
    run_time: datetime | str | None = None,
) -> tuple[list[RankedEntry], str]:
    """Join the complete registry to the three frozen-factor audits."""

    config = parse_human_factors(human_factors_path)
    f1 = _result_map(f1_payload, "F1 audit")
    f2 = _result_map(f2_payload, "F2 audit")
    f3 = _result_map(f3_payload, "F3 audit")
    included = registry.get("included_distributions")
    if not isinstance(included, list):
        raise ValueError("Registry has no included_distributions list.")
    names = {str(row["child"]) for row in included if isinstance(row, Mapping)}
    for label, values in (("F1", f1), ("F2", f2), ("F3", f3)):
        if set(values) != names:
            missing = sorted(names - set(values))
            extra = sorted(set(values) - names)
            raise ValueError(f"{label} child set differs from registry; missing={missing}, extra={extra}.")

    results: list[RankedEntry] = []
    for raw in included:
        if not isinstance(raw, Mapping):
            raise ValueError("Registry distribution row must be an object.")
        name = str(raw["child"])
        f1_row, f2_row, f3_row = f1[name], f2[name], f3[name]
        source_url = str(raw.get("distribution_source", ""))
        data_limit = str(raw.get("data_limit", ""))
        merged_at_distribution = not raw.get("regular_trading_start_date") and "merged into" in data_limit.casefold()
        entry = RegistryEntry(
            name=name,
            parent=str(raw.get("parent", "")),
            child_cik=str(raw.get("child_cik", "")),
            parent_cik=str(raw.get("parent_cik", "")),
            ratio=str(raw["ratio"]) if raw.get("ratio") is not None else None,
            record_date=_date(raw.get("record_date")),
            distribution_date=_date(raw.get("distribution_date")),
            form10=FilingReference(
                "10-12B",
                str(raw.get("form10_accession", "")),
                str(raw.get("form10_url", "")),
                str(raw.get("section", "")),
            ),
            distribution_8k=FilingReference(
                "8-K or transaction filing",
                _accession_from_url(source_url),
                source_url,
                "Distribution completion or final terms",
            ) if source_url else None,
            listing_approved=bool(raw.get("child_ticker")),
            regular_trading=bool(raw.get("regular_trading_start_date")),
            is_spinoff=not merged_at_distribution,
            drop_reason=(
                "distribution immediately followed by a merger; no standalone regularly traded security"
                if merged_at_distribution
                else None
            ),
            facts={"F1": f1_row.get("f1"), "F2": f2_row.get("f2"), "F3": f3_row.get("f3")},
        )
        closes: list[CloseRecord] = []
        if f1_row.get("child_close") and f1_row.get("pricing_date"):
            sources = f1_row.get("sources")
            closes.append(
                CloseRecord(
                    pricing_date=date.fromisoformat(str(f1_row["pricing_date"])),
                    instrument=str(raw.get("child_ticker", "")),
                    close=Decimal(str(f1_row["child_close"])),
                    currency=str(f1_payload.get("currency", "USD")),
                    source=str(sources[0]) if isinstance(sources, list) and sources else "Nasdaq official historical endpoint",
                )
            )
        scored = score_entry(
            entry,
            config.factors,
            run_date=date.fromisoformat(str(registry["run_date"])),
            window_start=config.window_start,
            window_end=config.window_end,
            closes=closes,
        )
        if entry.is_spinoff and scored.total_points is None and f1_row.get("data_limit"):
            scored = replace(scored, unranked_reason=f"factor F1 missing; {f1_row['data_limit']}")
        results.append(scored)

    watch = registry.get("registered_or_future_watch", [])
    if not isinstance(watch, list):
        raise ValueError("registered_or_future_watch must be a list.")
    for raw in watch:
        if not isinstance(raw, Mapping):
            raise ValueError("Future-watch row must be an object.")
        entry = RegistryEntry(
            name=str(raw["child"]),
            parent=str(raw.get("parent", "")),
            child_cik=str(raw.get("child_cik", "")),
            parent_cik=str(raw.get("parent_cik", "")),
            ratio=None,
            record_date=None,
            distribution_date=None,
            form10=FilingReference(
                str(raw.get("form", "10-12B/A")),
                str(raw.get("form10_accession", "")),
                str(raw.get("form10_url", "")),
                str(raw.get("section", "")),
            ),
            distribution_8k=None,
            facts={},
        )
        scored = score_entry(
            entry,
            config.factors,
            run_date=date.fromisoformat(str(registry["run_date"])),
            window_start=config.window_start,
            window_end=config.window_end,
        )
        results.append(replace(scored, unranked_reason=str(raw["reason"])))

    if form10_screen is not None:
        represented_ciks = {
            result.entry.child_cik.lstrip("0") or "0"
            for result in results
        }
        rows = form10_screen.get("registrants", [])
        if not isinstance(rows, list):
            raise ValueError("Form 10 screen has no registrants list.")
        fund_terms = re.compile(
            r"\b(?:fund|trust|reit|bdc|business development|private credit|lending|infrastructure strategies)\b",
            re.IGNORECASE,
        )
        for raw in rows:
            if not isinstance(raw, Mapping):
                raise ValueError("Form 10 screen row must be an object.")
            cik = str(raw.get("cik", "")).lstrip("0") or "0"
            if cik in represented_ciks:
                continue
            name = str(raw.get("company_name", "not available"))
            if raw.get("candidate") is False:
                reason = "deterministic filing-text screen found no spinoff or parent-distribution evidence"
            elif fund_terms.search(name):
                reason = "fund or investment-vehicle filing; no completed parent share distribution was established"
            else:
                reason = "latest Form 10 was screened, but no completed parent share distribution was established by the index date"
            filing_url = str(raw.get("filing_url", ""))
            filing = FilingReference(
                str(raw.get("form", "Form 10")),
                str(raw.get("accession", "not available")),
                filing_url,
                "Complete submission; deterministic filing-text screen",
            )
            dropped_entry = RegistryEntry(
                name=name,
                parent="",
                child_cik=str(raw.get("cik", "")),
                parent_cik="",
                ratio=None,
                record_date=None,
                distribution_date=None,
                form10=filing,
                distribution_8k=None,
                is_spinoff=False,
                drop_reason=reason,
            )
            results.append(
                score_entry(
                    dropped_entry,
                    config.factors,
                    run_date=date.fromisoformat(str(registry["run_date"])),
                    window_start=config.window_start,
                    window_end=config.window_end,
                )
            )
    report = render_report(
        results,
        run_date=date.fromisoformat(str(registry["run_date"])),
        price_date=config.index_date,
        index_date=config.index_date,
        post_distribution_window_days=config.post_distribution_window_days,
        run_time=run_time,
    )
    return results, report


def render_evidence(
    registry: Mapping[str, Any],
    f1_payload: Mapping[str, Any],
    f2_payload: Mapping[str, Any],
    f3_payload: Mapping[str, Any],
) -> str:
    """Render concise, source-linked evidence for every included distribution."""

    f1 = _result_map(f1_payload, "F1 audit")
    f2 = _result_map(f2_payload, "F2 audit")
    f3 = _result_map(f3_payload, "F3 audit")
    lines = [
        "# Full Seeker Evidence",
        "",
        f"Run date: {registry['run_date']}",
        "",
        "Scope: SEC Form 10/CERT discovery from January 1, 2024 through the November 19, 2026 index date, followed by filing review for distributions in the frozen trailing-year window.",
        "",
        "Missing facts remain missing. The audit does not estimate amounts, dates, prices, or transactions.",
    ]
    for raw in registry["included_distributions"]:
        name = str(raw["child"])
        one, two, three = f1[name], f2[name], f3[name]
        lines.extend(["", f"## {name}", ""])
        lines.append(
            f"- Registry: child CIK {raw['child_cik']}; parent {raw['parent']} (CIK {raw['parent_cik']}); "
            f"record date {raw['record_date']}; distribution date {raw['distribution_date']}; ratio {raw.get('ratio') or 'not available'}."
        )
        lines.append(
            f"- Form 10: accession {raw['form10_accession']}; section {raw['section']}; <{raw['form10_url']}>."
        )
        if one.get("child_close"):
            price_text = f"child close ${one['child_close']} USD on {one['pricing_date']}"
            if one.get("parent_close"):
                price_text += f"; parent close ${one['parent_close']} USD on the same date"
            if one.get("market_cap_ratio"):
                ratio_pct = Decimal(str(one["market_cap_ratio"])) * Decimal("100")
                price_text += f"; derived child/parent market-cap ratio {ratio_pct:.3f}%"
            f1_value = "missing" if one.get("f1") is None else str(one["f1"]).lower()
            lines.append(f"- F1: {f1_value}; {price_text}.")
        else:
            limit = str(one.get("data_limit") or "required price fact unavailable").rstrip(".")
            lines.append(f"- F1: missing; {limit}.")
        for source in one.get("sources", []):
            lines.append(f"  - Official close source: <{source}>.")
        if two.get("payment_amount_usd") is not None:
            payment = f"${Decimal(str(two['payment_amount_usd'])):,.0f} USD"
        elif two.get("payment_minimum_usd") is not None:
            payment = (
                f"${Decimal(str(two['payment_minimum_usd'])):,.0f} to "
                f"${Decimal(str(two['payment_maximum_usd'])):,.0f} USD"
            )
        else:
            payment = "not available"
        lines.append(f"- F2: {str(two.get('f2')).lower()}; debt-funded parent payment {payment}. {two['filing_fact']}")
        for source in two["sources"]:
            lines.append(
                f"  - SEC source: accession {source.get('accession', 'not available')}; "
                f"section {source['section']}; <{source['url']}>."
            )
        lines.append(
            f"- F3: {str(three.get('f3')).lower()}; {three.get('form4_filings_found', 0)} Form 4/4-A filings reviewed; "
            f"transaction codes {', '.join(three.get('transaction_codes', [])) or 'none'}; "
            f"qualifying code-P purchases {len(three.get('qualifying_purchases', []))}."
        )
        for purchase in three.get("qualifying_purchases", []):
            lines.append(
                f"  - Qualifying purchase: {purchase['transaction_date']}; accession {purchase['accession']}; <{purchase['url']}>."
            )
    lines.extend([
        "",
        "## Saved machine-readable audit files",
        "",
        "- `registry.json`: distribution registry and filing provenance.",
        "- `official_close_f1_audit.json`: first regular closes and market-cap ratios.",
        "- `sec_f2_audit.json`: filing-based separation payment evidence.",
        "- `form4_f3_audit.json`: complete eligible-window Form 4 review.",
        "",
        "This evidence supports a screen, not an investment recommendation.",
    ])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the complete Week 4 seeker report.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--f1", required=True, type=Path)
    parser.add_argument("--f2", required=True, type=Path)
    parser.add_argument("--f3", required=True, type=Path)
    parser.add_argument("--form10-screen", required=True, type=Path)
    parser.add_argument("--human-factors", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--evidence-output", required=True, type=Path)
    parser.add_argument("--run-time", default="", help="Saved ISO 8601 run time")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    registry = _read_json(args.registry)
    f1 = _read_json(args.f1)
    f2 = _read_json(args.f2)
    f3 = _read_json(args.f3)
    form10_screen = _read_json(args.form10_screen)
    run_time = args.run_time or datetime.now().astimezone().isoformat()
    results, report = build_results(
        registry,
        f1,
        f2,
        f3,
        args.human_factors,
        form10_screen,
        run_time=run_time,
    )
    args.report_output.write_text(report, encoding="utf-8")
    args.evidence_output.write_text(render_evidence(registry, f1, f2, f3), encoding="utf-8")
    ranked = sum(result.total_points is not None for result in results)
    watch = sum(
        result.total_points is None
        and result.entry.is_spinoff
        and not result.entry.regular_trading
        for result in results
    )
    dropped = sum(not result.entry.is_spinoff for result in results)
    print(f"Saved report with {ranked} ranked, {watch} watch, and {dropped} dropped rows.")


if __name__ == "__main__":
    main()
