import tempfile
import unittest
from pathlib import Path

from week02.desk_app import (
    bounded_line_labeled_text,
    extract_release_period,
    find_item_heading,
    quarterly_revenue_growth_from_rows,
)
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
    def test_bounded_release_context_keeps_line_labels_and_whole_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exhibit-99-1.txt"
            path.write_text("first line\nsecond line\nthird line\n", encoding="utf-8")
            excerpt = bounded_line_labeled_text(path, max_characters=60)
        self.assertIn("exhibit-99-1.txt:1: first line", excerpt)
        self.assertNotIn("third li", excerpt)
        self.assertTrue(all(line.count(":") >= 2 for line in excerpt.splitlines()))

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

    def test_release_eps_prefers_gaap_diluted_over_adjusted(self):
        lines = [
            "Adjusted income per diluted share | $ | 2.26 | $ | 1.97",
            "GAAP income (loss) per diluted share | $ | (0.29) | $ | 1.41",
        ]
        candidates = source_candidates(lines, "diluted_eps")
        self.assertEqual(candidates[0]["line_start"], 2)
        self.assertEqual(candidates[0]["text"], lines[1])

    def test_release_eps_prefers_diluted_row_in_operations_statement(self):
        lines = [
            "Diluted EPS | $ | 0.59 | $ | 0.56 | $ | 1.23 | $ | 0.80 | $ | 0.87",
            "Q3 diluted EPS for the quarter was $0.87.",
            "Netflix, Inc.",
            "Consolidated Statements of Operations",
            "Earnings per share*:",
            "Diluted | $ | 0.87 | $ | 0.80 | $ | 0.59",
        ]
        candidates = source_candidates(lines, "diluted_eps")
        self.assertEqual(candidates[0]["line_start"], 6)

    def test_item_heading_matches_wrapped_title_and_skips_table_of_contents(self):
        lines = [
            "Item 1. | Business | 1",
            "PART I",
            "Item 1.",
            "Business",
            "Item 1A.",
            "Risk Factors",
            "Item 7.",
            "Management’s Discussion and Analysis of Financial Condition and Results of Operations",
            "Item 7A.",
            "Quantitative and Qualitative Disclosures About Market Risk",
        ]
        self.assertEqual(find_item_heading(lines, "1", r"\bbusiness\b"), 2)
        self.assertEqual(find_item_heading(lines, "1A", r"risk factors"), 4)
        self.assertEqual(find_item_heading(lines, "7", r"management.?s discussion and analysis"), 6)
        self.assertEqual(find_item_heading(lines, "7A", r"quantitative and qualitative disclosures"), 8)

    def test_quarter_growth_matches_prior_year_period_not_prior_quarter(self):
        lines = [
            "Three Months Ended | Nine Months Ended",
            "September 30, 2026 | June 30, 2026 | September 30, 2025 | September 30, 2026 | September 30, 2025",
            "Revenues | $ | 12,874,176 | $ | 12,559,938 | $ | 11,510,307 | $ | 37,683,871 | $ | 33,132,274",
        ]
        result = quarterly_revenue_growth_from_rows(lines, 3, "September 30, 2026")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["current_quarter_revenue_thousands"], 12_874_176)
        self.assertEqual(result["prior_year_same_quarter_revenue_thousands"], 11_510_307)
        self.assertAlmostEqual(result["result_percent"], 11.8491, places=4)

    def test_release_revenue_prefers_consolidated_revenues_row(self):
        lines = [
            "Record revenues of $966 million, up 38% y/y",
            "BELDEN INC.",
            "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS",
            "Three Months Ended | Nine Months Ended",
            "September 27, 2026 | September 28, 2025 | September 27, 2026 | September 28, 2025",
            "(In thousands, except per share data)",
            "Revenues | $ | 965,954 | $ | 698,221 | $ | 2,412,486 | $ | 1,995,074",
        ]
        lines.extend([""] * 41)
        lines.append("Revenues | $ | 965,954 | $ | 698,221 | $ | 2,412,486 | $ | 1,995,074")
        candidates = source_candidates(lines, "total_revenue")
        self.assertEqual(candidates[0]["line_start"], 7)

    def test_release_period_supports_month_and_week_statements(self):
        costco_lines = ["16 Weeks Ended | 16 Weeks Ended | 52 Weeks Ended", "August 30, 2026 | August 31, 2025"]
        walmart_lines = ["Three Months Ended | Six Months Ended", "July 31, | July 31,", "(Amounts in millions) | 2026 | 2025"]
        self.assertEqual(extract_release_period(costco_lines)[0], "August 30, 2026")
        self.assertEqual(extract_release_period(walmart_lines)[0], "July 31, 2026")


if __name__ == "__main__":
    unittest.main()
