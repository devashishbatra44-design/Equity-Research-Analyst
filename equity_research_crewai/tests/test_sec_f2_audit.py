from decimal import Decimal

import pytest

from equity_research_crewai.sec_f2_audit import classify_f2


def test_classify_f2_exact_zero_is_true() -> None:
    assert classify_f2({"payment_amount_usd": "0"}) is True


def test_classify_f2_positive_exact_amount_is_false() -> None:
    assert classify_f2({"payment_amount_usd": "4100000000"}) is False


def test_classify_f2_positive_range_is_false() -> None:
    assert classify_f2(
        {"payment_minimum_usd": Decimal("726000000"), "payment_maximum_usd": "776000000"}
    ) is False


def test_classify_f2_range_including_zero_is_missing() -> None:
    assert classify_f2({"payment_minimum_usd": "0", "payment_maximum_usd": "1"}) is None


def test_classify_f2_rejects_partial_range() -> None:
    with pytest.raises(ValueError, match="both minimum and maximum"):
        classify_f2({"payment_minimum_usd": "1"})
