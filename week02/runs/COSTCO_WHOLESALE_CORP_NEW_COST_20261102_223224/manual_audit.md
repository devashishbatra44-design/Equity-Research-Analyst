# Manual Report Audit — COST

Use the course audit checklist. Devashish previously checked these same figures and sources by hand in the October 31 Costco audit. This rerun has the same financial inputs; the previously unavailable quarter-growth item is now shown explicitly as the same hand-checked calculation.

Counts at top: Errors (wrong + unsupported): **0**. Missing: **0**.

| # | Required claim | Expected value to compare with report | Filing/source reference | Mark by student | Filing value or note |
|---:|---|---|---|---|---|
| 1 | Total revenue, latest fiscal year | $303,154 million | 10-K accession 0000909832-26-000093; tag us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | **Correct (student-checked)** | Same FY2026 figure as the October 31 hand audit. |
| 2 | Revenue growth versus prior year | 10.1437% | Formula: (Current-year revenue - Prior-year revenue) / Prior-year revenue | **Correct (student-checked)** | Same inputs and arithmetic as the October 31 hand audit; exact result 10.1436953876%. |
| 3 | Operating income and operating margin | $11,685 million; 3.8545% | 10-K tag us-gaap:OperatingIncomeLoss; margin formula: Current-year operating income / Current-year total revenue | **Correct (student-checked)** | Same filing values; $11,685 / $303,154 = 3.8545%. |
| 4 | Net income attributable to the company | $9,226 million | 10-K tag us-gaap:NetIncomeLoss | **Correct (student-checked)** | Same FY2026 value as the October 31 hand audit. |
| 5 | Diluted earnings per share, GAAP | $20.76 | 10-K tag us-gaap:EarningsPerShareDiluted | **Correct (student-checked)** | Same GAAP diluted EPS as the October 31 hand audit. |
| 6 | Return on average equity | 28.4021% | Formula: Current-year net income / average current-and-prior equity | **Correct (student-checked)** | Same inputs and arithmetic as the October 31 hand audit. |
| 7 | Debt to equity, current debt included | 0.1721x | Formula: (Long-term debt + Current portion of long-term debt) / Stockholders' equity | **Correct (student-checked)** | Same debt and equity inputs as the October 31 hand audit: (3,914 + 2,248) / 35,803 = 0.1721x. |
| 8 | Free cash flow | $9,382 million | Formula: Net cash from operations - Additions to property and equipment | **Correct (student-checked)** | Same inputs and arithmetic as the October 31 hand audit: $15,817 - $6,435 = $9,382 million. |
| 9 | Latest quarter revenue | $95,723 as stated in the release | Exhibit 99.1 source line 39 | **Correct (student-checked)** | Same Exhibit 99.1 value as the October 31 hand audit. |
| 10 | Quarterly revenue growth versus same quarter last year | 11.1043% \| (95,723 - 86,156) / 86,156 | exhibit-99-1.txt:35: August 30, 2026 \| August 31, 2025 \| August 30, 2026 \| August 31, 2025 ; exhibit-99-1.txt:39: Total revenue \| 95,723 \| 86,156 \| 303,154 \| 275,235 | **Correct (student-checked)** | Same two quarter values and calculation previously checked by Devashish: 11.10% rounded; exact 11.1043%. |
| 11 | Quarterly diluted EPS, GAAP | $6.75 | Exhibit 99.1 source line 20 | **Correct (student-checked)** | Same GAAP diluted EPS as the October 31 hand audit. |

## Other Financial Analyst numbers

Check each peer, extra ratio, and P/E in the report. These are expected calculations and source trails, not audit marks.

| Report claim | Filing/source value | Mark by student | Note |
|---|---|---|---|
| FY-EPS P/E | 47.7905x = 992.13 / 20.76; close 2026-10-27; EPS period 2026-08-30, tag us-gaap:EarningsPerShareDiluted, accession 0000909832-26-000093 | **Correct (student-checked)** | Devashish previously checked the Nasdaq close and arithmetic in the October 31 hand audit. https://api.nasdaq.com/api/quote/COST/historical?assetclass=stocks&fromdate=2026-10-27&todate=2026-10-31&limit=100 |
| WMT operating margin | 4.1821% = 29,825 / 713,163 million | **Correct (student-checked)** | Same Walmart 10-K values and arithmetic as previously checked; period end 2026-01-31; accession 0000104169-26-000055. |
| TGT operating margin | 4.8836% = 5,117 / 104,780 million | **Correct (student-checked; source label corrected)** | Target's 10-K calls $104,780 million **Net sales**, not total revenue. $5,117 / $104,780 = 4.8836%; fiscal 2025 ended 2026-01-31; accession 0000027419-26-000016. The saved report now uses the filing's exact line label. |
| BJ operating margin | 3.8057% = 816.604 / 21,457.274 million | **Correct (student-checked)** | BJ's 10-K reports total revenues of $21,457,274 thousand and operating income of $816,604 thousand (equivalent to $21,457.274 million and $816.604 million); margin = 816.604 / 21,457.274 = 3.805721%, or 3.8057%; fiscal 2025 ended 2026-01-31; accession 0001531152-26-000007. |

## Report checks

- Template: all five required parts are present in the generated draft: **Present (student-checked)**.
- Recommendation: **Hold**, using the 47.79x FY-EPS P/E and checked operating evidence; Devashish previously approved this working judgment and verified the figures it cites.

## Partner check on the separate partner-pick report

- Partner claim 1 and mark: ______________________________
- Partner claim 2 and mark: ______________________________
- Partner name and initials: ______________________________

Source folder: `COSTCO_WHOLESALE_CORP_NEW_COST_20261102_223224`.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built the desk; Purdue GenAI Studio generated the draft. Devashish checked the same figures and filings in the October 31 audit and confirmed the unchanged values in this run.

Any remaining errors are my own.
