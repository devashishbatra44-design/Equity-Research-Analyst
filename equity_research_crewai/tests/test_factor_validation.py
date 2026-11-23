from datetime import date
from decimal import Decimal

import pytest

from equity_research_crewai.factor_validation import render_baseline, validate_config
from equity_research_crewai.spinoff_seeker import (
    FactorPoint,
    FilingReference,
    RankedEntry,
    RegistryEntry,
    Stage,
)


def config() -> dict[str, object]:
    return {
        "status": "frozen",
        "human_owner": "Human Owner",
        "approval_statement": "approved",
        "approved_on": "2026-11-21",
        "signal_date": "2026-11-19",
        "horizon_calendar_days": 90,
        "outcome_date_on_or_after": "2027-02-17",
        "expected_ranked_names": 1,
        "comparisons": [
            {"id": "F1", "statistics": ["mean", "median"]},
            {"id": "F2", "statistics": ["mean", "median"]},
            {"id": "F3", "statistics": ["mean", "median"]},
            {"id": "COMPOSITE", "statistics": ["mean", "median"]},
        ],
    }


def result() -> RankedEntry:
    entry = RegistryEntry(
        name="Spin Company",
        parent="Parent Company",
        child_cik="1",
        parent_cik="2",
        ratio="1 for 1",
        record_date=date(2026, 1, 1),
        distribution_date=date(2026, 1, 15),
        form10=FilingReference("10-12B", "0001", "https://example.test", "The Spin-Off"),
        distribution_8k=None,
        facts={"F1": True, "F2": False, "F3": True},
    )
    return RankedEntry(
        entry,
        Stage.IN_WINDOW,
        (
            FactorPoint("F1", True, Decimal("1")),
            FactorPoint("F2", False, Decimal("0")),
            FactorPoint("F3", True, Decimal("1")),
        ),
        Decimal("2"),
        None,
        None,
    )


def test_frozen_design_requires_four_unique_comparisons() -> None:
    value = config()
    value["comparisons"] = [{"id": "F1"}]
    with pytest.raises(ValueError, match="exactly 4"):
        validate_config(value)


def test_frozen_design_requires_exact_outcome_date() -> None:
    value = config()
    value["outcome_date_on_or_after"] = "2027-02-18"
    with pytest.raises(ValueError, match="signal date plus"):
        validate_config(value)


def test_baseline_reads_no_return_and_prints_frozen_universe() -> None:
    text = render_baseline(
        [result()],
        config(),
        config_sha256="abc123",
        tickers={"Spin Company": "SPIN"},
    )
    assert "Returns read by this baseline command: 0" in text
    assert "Planned group definitions: 4" in text
    assert "Planned statistical comparisons: 8" in text
    assert "| SPIN | Spin Company | true | false | true | 2 |" in text
