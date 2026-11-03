# Manual Report Audit — BDC

This audit applies to the unedited desk output in `report.md`. Devashish checked the filing values and arithmetic by hand. The report and filing values are shown side by side.

Errors (wrong + unsupported): **0**. Missing: **0**. Core-claim errors: **0**.

| # | Required claim | Report said | Filing says | Filing/source reference | Mark by student |
|---:|---|---|---|---|---|
| 1 | Total revenue, latest fiscal year | $2,715,194,000 | $2,715,194,000 | 10-K accession `0000913142-26-000009`; `us-gaap:Revenues`; year ended 2025-12-31 | **Correct** |
| 2 | Revenue growth versus prior year | 10.33% | 10.3298% = (2,715,194 − 2,460,979) / 2,460,979 | Same 10-K, FY2025 and FY2024 revenue | **Correct** |
| 3 | Operating income and operating margin | $315,692,000; 11.63% | $315,692,000; 11.6269% = 315,692 / 2,715,194 | Same 10-K; `us-gaap:OperatingIncomeLoss`; year ended 2025-12-31 | **Correct** |
| 4 | Net income attributable to the company | $237,522,000 | $237,522,000 | Same 10-K; `us-gaap:NetIncomeLoss`; year ended 2025-12-31 | **Correct** |
| 5 | Diluted EPS, GAAP | $5.91 | $5.91 | Same 10-K; `us-gaap:EarningsPerShareDiluted`; year ended 2025-12-31 | **Correct** |
| 6 | Return on average equity | 18.56% | 18.5625% = 237,522 / ((1,264,424 + 1,294,736) / 2) | Same 10-K; FY2025 net income and FY2025/FY2024 equity | **Correct** |
| 7 | Debt to equity, current debt included | 1.02x, including current debt of $0 | 1.0168x = (1,285,666 + 0) / 1,264,424 | Same 10-K; `LongTermDebtNoncurrent`; `10-k.txt:2713` states $1.3 billion of principal payments, none due in 2026 | **Correct** |
| 8 | Free cash flow | $218,692,000 | $218,692,000 = 354,864 − 136,172 | Same 10-K; cash from operations less additions to PP&E | **Correct** |
| 9 | Latest-quarter revenue | $965,954,000 | $965,954,000 | 8-K accession `0000913142-26-000039`, Exhibit 99.1, quarter ended 2026-09-27 | **Correct** |
| 10 | Quarter revenue growth versus same quarter last year | 38.35% | 38.3450% = (965,954 − 698,221) / 698,221 | Same Exhibit 99.1; Q3 2026 and Q3 2025 revenue | **Correct** |
| 11 | Quarter diluted EPS, GAAP | $(0.29) | $(0.29) | Same Exhibit 99.1; GAAP diluted EPS for quarter ended 2026-09-27 | **Correct** |

## Other Financial Analyst numbers

| Report claim | Report said | Filing/source says | Mark by student | Note |
|---|---|---|---|---|
| FY-EPS P/E | 18.05x = 106.66 / 5.91 | 18.0474x; $106.66 BDC close on 2026-10-28, manually verified by Devashish in LSEG Workspace | **Correct** | The valuation input and arithmetic are supported by the LSEG check. Provenance note: the generated `report.md` still cites StockAnalysis for this same close; that original citation is preserved and was not rewritten. |
| APH operating margin | 25.41% | 25.4110% = 5,868.6 / 23,094.7; 10-K accession `0001104659-26-013549` | **Correct** | Fiscal year ended 2025-12-31. |
| TEL operating margin | 18.60% | 18.6016% = 3,211 / 17,262; 10-K accession `0001104659-25-109150` | **Correct** | Fiscal year ended 2025-09-26. |
| GLW operating margin | 14.58% | 14.5819% = 2,279 / 15,629; 10-K accession `0000024741-26-000124` | **Correct** | Fiscal year ended 2025-12-31. |

## Report checks

- Template: all five required parts are present. **Correct**.
- Recommendation: **Hold**. It names the 18.05x FY-EPS P/E as the deciding number. The multiple is supported by the LSEG-verified October 28 close and FY2025 diluted EPS. **Correct**. The report's original StockAnalysis citation remains disclosed in the P/E note above.

## Partner check on Devashish’s Belden report

These marks were transcribed by Devashish from Shivani Rathi’s message. Each row contains one core claim and uses the course mark name.

| Core claim checked by Shivani | Filing value | Source | Shivani’s mark |
|---|---:|---|---|
| Claim 1 — FY2025 total revenue | $2,715,194,000 | 10-K accession `0000913142-26-000009`; Consolidated Statements of Operations | **Correct** |
| Claim 9 — Q3 2026 revenue | $965,954,000, reported as $966 million | 8-K accession `0000913142-26-000039`, Exhibit 99.1 | **Correct** |

Partner: Shivani Rathi (SR).

Source folder: `BELDEN_INC_BDC_20261102_233949`.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built the desk; Purdue GenAI Studio generated the draft. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
