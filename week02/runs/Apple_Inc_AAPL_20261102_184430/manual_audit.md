# Manual Report Audit — AAPL

This audit applies to the unedited desk output in `report.md`. Devashish checked the filing values and arithmetic by hand. The report and filing values are shown side by side.

Errors (wrong + unsupported): **0**. Missing: **0**.

| # | Required claim | Report said | Filing says | Filing/source reference | Mark by student |
|---:|---|---|---|---|---|
| 1 | Total revenue, latest fiscal year | $416,161 million | $416,161 million | 10-K accession `0000320193-25-000079`; `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; year ended 2025-09-27 | **Correct** |
| 2 | Revenue growth versus prior year | 6.43% | 6.4255% = (416,161 − 391,035) / 391,035 | Same 10-K, FY2025 and FY2024 revenue | **Correct** |
| 3 | Operating income and operating margin | $133,050 million; 31.97% | $133,050 million; 31.9708% = 133,050 / 416,161 | Same 10-K; `us-gaap:OperatingIncomeLoss`; year ended 2025-09-27 | **Correct** |
| 4 | Net income attributable to the company | $112,010 million | $112,010 million | Same 10-K; `us-gaap:NetIncomeLoss`; year ended 2025-09-27 | **Correct** |
| 5 | Diluted EPS, GAAP | $7.46 | $7.46 | Same 10-K; `us-gaap:EarningsPerShareDiluted`; year ended 2025-09-27 | **Correct** |
| 6 | Return on average equity | 171.42% | 171.4224% = 112,010 / ((73,733 + 56,950) / 2) | Same 10-K; FY2025 net income and FY2025/FY2024 equity | **Correct** |
| 7 | Debt to equity, current debt included | 1.23x | 1.2298x = (78,328 + 12,350) / 73,733 | Same 10-K; noncurrent debt, current debt, and equity at 2025-09-27 | **Correct** |
| 8 | Free cash flow | $98,767 million | $98,767 million = 111,482 − 12,715 | Same 10-K; cash from operations less additions to PP&E | **Correct** |
| 9 | Latest-quarter revenue | $114.5 billion | $114.5 billion | 8-K accession `0000320193-26-000024`, Exhibit 99.1, quarter ended 2026-09-26 | **Correct** |
| 10 | Quarter revenue growth versus same quarter last year | 12% | Issuer reports “up 12 percent year over year” | Same Exhibit 99.1 | **Correct** |
| 11 | Quarter diluted EPS, GAAP | $2.10 | $2.10 | Same Exhibit 99.1; GAAP diluted EPS for quarter ended 2026-09-26 | **Correct** |

## Other Financial Analyst numbers

| Report claim | Report said | Filing/source says | Mark by student | Note |
|---|---|---|---|---|
| FY-EPS P/E | 46.53x = 347.10 / 7.46 | 46.5282x from the October 27, 2026 Nasdaq close and FY2025 GAAP diluted EPS | **Correct** | Backward-looking FY-EPS P/E, not TTM P/E. [Nasdaq source](https://api.nasdaq.com/api/quote/AAPL/historical?assetclass=stocks&fromdate=2026-10-27&todate=2026-10-31&limit=100) |
| MSFT operating margin | 46.78% | 46.7808% = 155,237 / 331,839; 10-K accession `0001193125-26-323660` | **Correct** | Fiscal year ended 2026-06-30. |
| GOOGL operating margin | 32.03% | 32.0326% = 129,039 / 402,836; 10-K accession `0001652044-26-000018` | **Correct** | Fiscal year ended 2025-12-31. |
| AMZN operating margin | 11.16% | 11.1553% = 79,975 / 716,924; 10-K accession `0001018724-26-000004` | **Correct** | Fiscal year ended 2025-12-31. |

The former FY2026 annual additions are preserved in `student_notes.md`. They are not marked here because they were not part of the desk-generated report.

## Report checks

- Template: all five required parts are present. **Correct**.
- Recommendation: **Hold**. It names the checked 46.53x FY-EPS P/E and states the valuation limitation. **Correct**.

Source folder: `Apple_Inc_AAPL_20261102_184430`.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built the desk; Purdue GenAI Studio generated the draft. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
