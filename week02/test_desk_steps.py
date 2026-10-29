import unittest

from week02.desk_steps import (
    CONCEPTS,
    calculate_measures,
    normalize_ticker,
    parse_peers,
)


def observation(value, end="2026-08-30", start="2025-09-01"):
    return {"value": value, "period_end": end, "period_start": start}


class DeskStepsTests(unittest.TestCase):
    def test_normalizes_ticker_and_peers(self):
        self.assertEqual(normalize_ticker(" abc "), "ABC")
        self.assertEqual(parse_peers("abc,XYZ,abc"), ["ABC", "XYZ"])

    def test_revenue_candidates_put_total_revenue_first(self):
        tags = CONCEPTS["total_revenue"]["tags"]
        self.assertEqual(tags[0], "Revenues")
        self.assertIn("RevenueFromContractWithCustomerExcludingAssessedTax", tags)

    def test_calculations_use_total_revenue_and_current_debt(self):
        concepts = {
            "total_revenue": {"current": observation(120), "prior": observation(100, "2025-08-31", "2024-09-02")},
            "operating_income": {"current": observation(12)},
            "net_income": {"current": observation(8)},
            "diluted_eps": {"current": observation(4)},
            "stockholders_equity": {"current": observation(50), "prior": observation(40, "2025-08-31")},
            "long_term_debt": {"current": observation(20)},
            "current_long_term_debt": {"current": observation(5)},
            "cash_from_operations": {"current": observation(15)},
            "property_equipment_additions": {"current": observation(3)},
        }
        data = calculate_measures({"concepts": concepts}, 40)
        calculations = data["calculations"]
        self.assertAlmostEqual(calculations["revenue_growth"]["result"], 0.2)
        self.assertAlmostEqual(calculations["operating_margin"]["result"], 0.1)
        self.assertAlmostEqual(calculations["debt_to_equity"]["result"], 0.5)
        self.assertEqual(calculations["free_cash_flow"]["result"], 12)
        self.assertEqual(calculations["price_to_earnings"]["result"], 10)


if __name__ == "__main__":
    unittest.main()
