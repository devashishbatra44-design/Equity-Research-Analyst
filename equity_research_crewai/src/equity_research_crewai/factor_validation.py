"""Freeze and render the baseline for the team-owned spinoff factor check."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from .build_full_seeker_report import build_results
from .spinoff_seeker import RankedEntry


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("status") != "frozen":
        raise ValueError("The factor-check design must be frozen.")
    if not str(config.get("human_owner", "")).strip():
        raise ValueError("The frozen design must name a human owner.")
    if not str(config.get("approval_statement", "")).strip():
        raise ValueError("The frozen design must contain the human approval statement.")
    comparisons = config.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 4:
        raise ValueError("The frozen design must contain exactly 4 planned comparisons.")
    comparison_ids = [str(row.get("id", "")) for row in comparisons if isinstance(row, Mapping)]
    if len(comparison_ids) != 4 or len(set(comparison_ids)) != 4:
        raise ValueError("Each planned comparison must have a unique ID.")
    signal_date = date.fromisoformat(str(config["signal_date"]))
    horizon = int(config["horizon_calendar_days"])
    outcome_date = date.fromisoformat(str(config["outcome_date_on_or_after"]))
    if horizon <= 0 or signal_date + timedelta(days=horizon) != outcome_date:
        raise ValueError("The outcome date must equal the signal date plus the frozen horizon.")


def render_baseline(
    results: Sequence[RankedEntry],
    config: Mapping[str, Any],
    *,
    config_sha256: str,
    tickers: Mapping[str, str],
) -> str:
    validate_config(config)
    ranked = sorted(
        (result for result in results if result.total_points is not None),
        key=lambda result: (-result.total_points, result.entry.name),
    )
    expected = int(config["expected_ranked_names"])
    if len(ranked) != expected:
        raise ValueError(f"Expected {expected} ranked names; found {len(ranked)}.")
    lines = [
        "# Frozen Spinoff Factor-Check Baseline",
        "",
        f"Human owner: {config['human_owner']}",
        f"Approved on: {config['approved_on']}",
        f"Frozen configuration SHA-256: `{config_sha256}`",
        f"Signal date: {config['signal_date']}",
        f"Outcome date: first official regular close on or after {config['outcome_date_on_or_after']}",
        f"Ranked universe: {len(ranked)} names",
        f"Planned comparisons: {len(config['comparisons'])}",
        "Returns read by this baseline command: 0",
        "",
        "| Ticker | Company | F1 | F2 | F3 | Frozen score |",
        "|---|---|---|---|---|---:|",
    ]
    for result in ranked:
        factor_values = {
            point.factor_id: "missing" if point.matched is None else str(point.matched).lower()
            for point in result.factor_points
        }
        lines.append(
            f"| {tickers.get(result.entry.name, 'not available')} | {result.entry.name} | "
            f"{factor_values.get('F1', 'missing')} | {factor_values.get('F2', 'missing')} | "
            f"{factor_values.get('F3', 'missing')} | {result.total_points} |"
        )
    lines.extend(
        [
            "",
            "Status: baseline frozen; the 90-day outcome is not observable before the frozen outcome date.",
            "",
            "This factor check tests a small screen sample. It does not validate an investment strategy and is not a recommendation.",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected a JSON object in {path}.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--f1", required=True, type=Path)
    parser.add_argument("--f2", required=True, type=Path)
    parser.add_argument("--f3", required=True, type=Path)
    parser.add_argument("--human-factors", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    if not isinstance(config, Mapping):
        raise ValueError("The frozen factor-check configuration must be an object.")
    registry = _read_json(args.registry)
    results, _ = build_results(
        registry,
        _read_json(args.f1),
        _read_json(args.f2),
        _read_json(args.f3),
        args.human_factors,
    )
    included = registry.get("included_distributions", [])
    tickers = {
        str(row["child"]): str(row.get("child_ticker") or "not available")
        for row in included
        if isinstance(row, Mapping)
    }
    output = render_baseline(
        results,
        config,
        config_sha256=hashlib.sha256(config_bytes).hexdigest(),
        tickers=tickers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
