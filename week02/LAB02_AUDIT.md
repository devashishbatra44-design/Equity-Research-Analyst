# Lab 02 — Filing and Calculation Audit

Audit date: October 31, 2026.

This audit checks the saved runs against the SEC filings. Amounts from the financial statements are in millions of U.S. dollars, except per-share data.

## Run evidence

- Costco command: `.venv/bin/python week02/desk_steps.py COST --peers WMT,TGT,BJ --price 992.13 --price-date 2026-10-27 --price-source 'https://api.nasdaq.com/api/quote/COST/historical?assetclass=stocks&fromdate=2026-10-27&todate=2026-10-31&limit=100'`
- Costco run folder: `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261031_191554`
- Walmart transfer command: `.venv/bin/python week02/desk_steps.py WMT --peers COST,TGT,BJ`
- Walmart run folder: `runs/Walmart_Inc_WMT_20261031_191931` (Step 6 rerun after the extraction fix)
- Program tests: `.venv/bin/python -m unittest week02.test_desk_steps`

The `$992.13` Costco price input is the unadjusted close on Tuesday, October 27, 2026, as Lab 03 requires. The value was checked against Nasdaq's historical-data endpoint: [Nasdaq historical data](https://api.nasdaq.com/api/quote/COST/historical?assetclass=stocks&fromdate=2026-10-27&todate=2026-10-31&limit=100). The earlier `$896.48` input was not the Tuesday close used for Lab 03, so the P/E has been corrected.

## Seven-step Costco check

| Step | Mark | Evidence |
|---|---|---|
| 1. Resolve ticker | Right | `COST` resolves to CIK `909832`, padded as `0000909832`. |
| 2. Select filings | Right | The program selected the FY2026 10-K, the May 2026 10-Q, and the September 24, 2026 8-K that reports Item 2.02. Each accession and Accepted time came from its EDGAR index page. |
| 3. Download documents | Right | The run saved readable text from the selected 10-K, 10-Q, 8-K, and `EX-99.1`. The Exhibit 99.1 source is `costex9918-k92426.htm`. |
| 4. Read annual facts | Right | All nine current facts end August 30, 2026. Each fact has a tag, unit, filing, accession, and prior-year comparison. The figures match the FY2026 10-K lines listed below. |
| 5. Calculate measures | Right | The calculations reproduce the arithmetic below from Step 4 inputs. The operating-margin denominator is total revenue. |
| 6. Read release lines | Right | The release line states total revenue of `$95,723 million` for the quarter and `$303,154 million` for the year. The release paragraph states fourth-quarter diluted EPS of `$6.75`. |
| 7. Process peers | Right | WMT, TGT, and BJ use their own latest fiscal years and their own XBRL facts. Each peer margin is operating income divided by total revenue. |

## Costco annual facts matched to the 10-K

Source: Costco FY2026 Form 10-K, accession `0000909832-26-000093`, fiscal year ended August 30, 2026.

| Claim | FY2026 value | XBRL tag | Saved 10-K line |
|---|---:|---|---:|
| Total revenue | `$303,154 million` | `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | 1281 |
| Operating income | `$11,685 million` | `us-gaap:OperatingIncomeLoss` | 1285 |
| Net income attributable to Costco | `$9,226 million` | `us-gaap:NetIncomeLoss` | 1291 |
| Diluted EPS | `$20.76` | `us-gaap:EarningsPerShareDiluted` | 1294 |
| Stockholders' equity | `$35,803 million` | `us-gaap:StockholdersEquity` | 1350 |
| Long-term debt, excluding current portion | `$3,914 million` | `us-gaap:LongTermDebtNoncurrent` | 1339 |
| Current portion of long-term debt | `$2,248 million` | `us-gaap:LongTermDebtCurrent` | 1335 |
| Net cash from operating activities | `$15,817 million` | `us-gaap:NetCashProvidedByUsedInOperatingActivities` | 1402 |
| Additions to property and equipment | `$6,435 million` | `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment` | 1404 |

The SEC cash-flow statement presents additions to property and equipment as `(6,435)`. The calculation preserves the SEC value and treats `$6,435 million` as a positive expenditure amount when subtracting it.

## Costco calculations redone by hand

| Measure | Arithmetic | Result |
|---|---|---:|
| Revenue growth | `(303,154 - 275,235) / 275,235` | `10.1437%` |
| Operating margin on total revenue | `11,685 / 303,154` | `3.8545%` |
| Return on average equity | `9,226 / ((35,803 + 29,164) / 2)` | `28.4021%` |
| Debt to equity | `(3,914 + 2,248) / 35,803` | `17.2108%` |
| Free cash flow | `15,817 - 6,435` | `$9,382 million` |
| Price divided by FY2026 diluted EPS | `992.13 / 20.76` | `47.7905x` |

The P/E is not labeled TTM P/E. It uses the supplied share price and FY2026 diluted EPS.

## Walmart transfer check

The unchanged program selected Walmart's Form 10-K for the fiscal year ended January 31, 2026.

| Check | Evidence | Mark |
|---|---|---|
| Total revenue | `$713,163 million`; `us-gaap:Revenues`; saved 10-K line 2111 | Right |
| Operating income | `$29,825 million`; `us-gaap:OperatingIncomeLoss`; saved 10-K line 2115 | Right |
| Total-revenue operating margin | `29,825 / 713,163 = 4.1821%` | Right |
| Revenue definition | The selected line is `Total revenues`, not net sales. | Right |
| Period alignment | Both inputs end January 31, 2026. | Right |

Walmart reports an operating-income percentage based on net sales elsewhere in its filing. This desk intentionally uses total revenue for every peer so the comparison keeps one denominator definition.

## Definition trap

Costco total revenue includes net sales and membership fees. Net sales alone is not total revenue. A margin based on net sales differs from a margin based on total revenue. The report must name its denominator.

## Partner verification

The code and filing evidence support the marks above. Lab 02 also requires a partner to check two marks.

- Partner mark 1 checked: ____________________
- Partner mark 2 checked: ____________________
- Partner initials: ____________________

Do not mark this partner requirement complete until the partner performs the check.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex was used to build and test the pipeline and to organize the audit. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
