import unittest

from week02.desk_app import extract_release_period
from week02.desk_steps import (
    CONCEPTS,
    Company,
    calculate_measures,
    format_observation,
    normalize_ticker,
    parse_peers,
    source_candidates,
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

    def test_comparative_fact_fiscal_year_uses_its_period_end(self):
        item = {
            "val": 100,
            "end": "2025-08-31",
            "fy": 2026,
            "fp": "FY",
            "form": "10-K",
            "filed": "2026-10-07",
            "accn": "",
            "source_unit_key": "USD",
        }
        fact = format_observation(Company("COST", "Example Corp", 1), "Revenues", CONCEPTS["total_revenue"], item)
        self.assertEqual(fact["fiscal_year"], 2025)

    def test_release_revenue_prefers_income_statement_over_constant_currency(self):
        lines = [
            "Walmart Inc. Condensed Consolidated Statements of Income (Unaudited)",
            "Total revenues | 187,937 | 177,402 | 5.9 | % | 365,688 | 343,011 | 6.6 | %",
            "The table below reflects constant currency for total revenues.",
            "Total revenues (cc) | $ | 34,081 | 7.9 | %",
        ]
        candidates = source_candidates(lines, "total_revenue")
        self.assertEqual(candidates[0]["line_start"], 2)
        self.assertEqual(candidates[0]["text"], lines[1])

    def test_release_revenue_extracts_prose_statement(self):
        lines = [
            "The Company posted quarterly revenue of $114.5 billion, up 12 percent year over year.",
            "The CEO said the September quarter revenue record reached $114.5 billion, up 12 percent from a year ago.",
        ]
        candidates = source_candidates(lines, "total_revenue")
        self.assertEqual(candidates[0]["line_start"], 1)
        self.assertEqual(candidates[0]["text"], lines[0])

    def test_release_period_supports_month_and_week_statements(self):
        costco_lines = ["16 Weeks Ended | 16 Weeks Ended | 52 Weeks Ended", "August 30, 2026 | August 31, 2025"]
        walmart_lines = ["Three Months Ended | Six Months Ended", "July 31, | July 31,", "(Amounts in millions) | 2026 | 2025"]
        self.assertEqual(extract_release_period(costco_lines)[0], "August 30, 2026")
        self.assertEqual(extract_release_period(walmart_lines)[0], "July 31, 2026")


if __name__ == "__main__":
    unittest.main()
