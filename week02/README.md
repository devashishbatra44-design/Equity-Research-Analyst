# Week 2 — The Desk, Then Make It Yours

Last checked: November 2, 2026.

## Arrival check

- Lab 01 is complete under the temporary private-repository instruction.
- Francis and Zhang (2026), Section 3.1 and Figure 2: user-confirmed read.
- Figure 1 is a workflow made from agent-like model calls. Code fixes the main path, JSON hand-offs, checklist, and one retry.
- The model-provider key is available locally. Lab 02 does not need it. Lab 03 does.

## Required one-line answers

**Which paper tool does EDGAR provide for free?**  
EDGAR provides the filings reader: filing metadata, 10-K and 10-Q documents, the earnings 8-K and Exhibit 99.1, and XBRL company facts.

**Where is the autonomy slider in this project?**  
The autonomy slider is the agent permission mode: it ranges from approval for tool actions to broader automatic access, while the human still validates the result.

**What may shrink the reported prediction edge on unseen companies and years?**  
The edge may shrink under distribution shift, accounting-definition changes, model changes, or data and replication errors that were not present in the study sample.

## Kim, Muhn, and Nikolaev reading note

The assigned November 2024 v2 draft reports the following in Table 2:

| Method | Accuracy | F1 |
|---|---:|---:|
| Naive | 49.11% | 53.02% |
| Analyst, one month | 52.71% | 54.48% |
| Analyst, three months | 55.95% | 55.33% |
| Analyst, six months | 56.68% | 56.85% |
| GPT without chain-of-thought instructions | 52.33% | 54.52% |
| GPT with chain-of-thought instructions | 60.35% | 60.90% |

The assigned comparison is 60.35% for GPT with the structured prompt versus 52.71% for analysts after one month, a difference of about 7.6 percentage points.

Current source status matters. The [arXiv record](https://arxiv.org/abs/2407.17866) now says that a co-author found inconsistencies in the data and analyses while attempting replication. The authors temporarily withdrew the working paper. Treat the numbers above as results reported in the assigned v2 draft, not as settled replicated evidence.

Sources: [assigned v2 PDF](https://arxiv.org/pdf/2407.17866v2), especially Table 2 on PDF page 53; [current arXiv record](https://arxiv.org/abs/2407.17866).

## Report-audit rules

- Every number needs its filing, period, units, and line or XBRL tag.
- Every ratio must show its inputs, definition, and arithmetic.
- The 11 core claims use the definitions in the course report audit.
- Audit marks are correct, wrong, unsupported, missing, or not in filings.
- Report both error and missing counts. Errors equal wrong plus unsupported.

Definition trap: Costco's total revenue includes net sales and membership fees. Net sales alone is not total revenue. Gross margin on net sales and gross margin on total revenue are different calculations. The report must name the chosen definition.

## Costco prework — matched to the 10-K and XBRL

Costco's latest 10-K reports the 52 weeks ended August 30, 2026. The consolidated statements of income state amounts in millions, except per-share data.

| Claim | 10-K value | XBRL evidence |
|---|---:|---|
| Net income attributable to Costco | $9,226 million | `us-gaap:NetIncomeLoss`; 9,226,000,000 USD; September 1, 2025–August 30, 2026 |
| GAAP diluted EPS | $20.76 per share | `us-gaap:EarningsPerShareDiluted`; 20.76 USD/share; September 1, 2025–August 30, 2026 |

Both facts are FY2026 facts from Form 10-K accession `0000909832-26-000093`, filed October 7, 2026. The fiscal period ends August 30, 2026.

Sources: [FY2026 10-K filing detail](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html), [FY2026 10-K](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm), and [Costco company facts](https://data.sec.gov/api/xbrl/companyfacts/CIK0000909832.json).

## Before Session 2 status

- [x] Finish every Lab 01 row.
- [x] Watch the Karpathy talk and record the autonomy-slider answer.
- [x] Read Francis and Zhang Section 3.1 and Figure 2.
- [x] Devashish completed the filing audit by hand; the total-revenue versus net-sales and Costco gross-margin definition trap is documented in the audit worksheet.
- [x] Devashish confirms reading the Kim, Muhn, and Nikolaev abstract; the 60.35% comparison, unseen-data limitation, and current withdrawal caveat are recorded above. His ability to explain them aloud is not independently verified here.
- [x] Match Costco net income and diluted EPS between the 10-K and XBRL facts.

## Before Session 3

- [x] Complete all seven Lab 02 steps.
- [x] Run the steps on Costco and validate every step against the filings.
- [x] Run the unchanged steps on WMT with selected peers.
- [x] Match WMT total revenue and operating income to its latest 10-K.
- [x] Confirm the WMT revenue tag represents total revenue, not net sales.
- [x] Recompute the WMT operating margin by hand.
- [x] Push the permitted code and saved facts. `.env`, downloaded filing text, and licensed raw data remain excluded.
- [x] Confirm the local key is present before the first model call in Lab 03. No key value was printed or saved.

## Lab 02 completed runs

- Costco full run: `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261031_191554`
- Walmart transfer run: `runs/Walmart_Inc_WMT_20261031_191931`; Step 6 was rerun after narrowing extraction to the consolidated income-statement row.
- Costco price input for Lab 03: `$992.13`, COST's unadjusted close on Tuesday, October 27, 2026. Source: [Nasdaq historical data](https://api.nasdaq.com/api/quote/COST/historical?assetclass=stocks&fromdate=2026-10-27&todate=2026-10-31&limit=100).
- Detailed hand-check record: `LAB02_AUDIT.md`

The local filing texts remain excluded from GitHub. The SEC-derived facts, calculations, filing metadata, peer tables, and manifests may be committed.

## Lab 03 — current status

- [x] Four model roles ran on COST: Research Analyst, Financial Analyst, Investment Advisor, and Strategy Manager.
- [x] The report has the five required headings; all eleven audit claims, FY-EPS P/E, and peer operating margins are present with source trails.
- [x] The Strategy Manager returned `pass` on the original report and on a fresh review of the updated report; both are structural reviews, not substitutes for the student's filing audit.
- [x] Reconciled the peer P/E update: `advisor_refresh.md` is the current Advisor output and matches the final Investment Recommendation; the original role output is retained as historical provenance. The targeted Strategy Manager check is in `manager_review_pe_reconciliation.json`.
- [x] The manual audit worksheet is saved beside the report at `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261031_191554/manual_audit.md`.
- [x] Devashish completed the 11 core-claim marks and checked the listed extra numbers by hand against the named filings. AI did not choose the audit marks.
- [x] Shivani Rathi selected Netflix (NFLX) as her company. Netflix material retained here supports the reciprocal partner review; it is not Devashish's own-company run.
- [x] Devashish reports that the reciprocal partner check is complete. Shivani's two checks of Devashish's Belden report are recorded in the Belden audit worksheet.
- [ ] Confirm the separate Checkpoint 1 upload in Brightspace. The generated report is not proof of an upload.

## Apple transfer run — November 2, 2026

- [x] Ran all seven data steps on AAPL. The latest available 10-K is FY2025; its annual facts are not the FY2026 quarter in the November 2 earnings release.
- [x] Used the October 27 close ($347.10) to match the COST price date. FY-EPS P/E is 46.5282x using FY2025 diluted EPS ($7.46); this is not TTM P/E.
- [x] Added Microsoft, Alphabet, and Amazon as broad technology benchmarks, not exact product substitutes. Their latest fiscal years differ, and the report names those periods.
- [x] Captured Apple’s prose-form release statement: quarterly revenue $114.5 billion, reported up 12% year over year, and diluted EPS $2.10. The growth figure is issuer-reported, not independently recomputed from two columns.
- [x] Ran the four model roles and received a passing structural Manager review. The report and manual worksheet are in `runs/Apple_Inc_AAPL_20261102_184430`.
- [x] Devashish compared the 11 core claims and listed supplemental Financial Analyst figures with the cited filings and source workbooks, and confirmed the template and recommendation checks.
- [x] The manual worksheet records the student's marks. Supplemental vendor forecasts and target prices were removed from the Week 2 report because the course rule permits filing facts and the supplied closing price, not unsupported forecast values.

The Apple run exposed that the Lab 02 release extractor did not recognize prose-form "quarterly revenue" disclosures. The extractor now captures that wording, and Lab 03 carries an issuer-reported year-over-year rate without presenting it as a code-computed ratio. A test covers the prose-form release line.

## Belden — Devashish's selected-company run — November 2, 2026

- [x] Ran all seven data steps on BDC using APH, TEL, and GLW as broad connectivity and communications peers.
- [x] Used the October 28 close ($106.66), the last close before Belden's October 29 earnings 8-K was accepted.
- [x] Added source parsing that prefers explicit GAAP diluted EPS over adjusted EPS and recognizes a `Revenues` row in the consolidated statement; tests pass.
- [x] Ran the four roles; the Strategy Manager returned `pass`. The report and completed manual audit are in `runs/BELDEN_INC_BDC_20261102_191754`.
- [x] Devashish completed the manual audit marks and counts. The XBRL reader did not return a current-debt tag for FY2025. The student checked the filed balance sheet and Note 15, found no current portion or 2026 principal maturity, and used $0 as the disclosed current portion in the debt/equity calculation.

## Netflix — Shivani Rathi's selected company — November 2, 2026

- [x] Retained the NFLX desk output as supporting material for the reciprocal review of Shivani's selected company.
- [x] Devashish reports that his reciprocal check of Shivani's Netflix work is complete.
- [x] The local Netflix worksheet is labeled as partner-review support. Its blank 11-claim table is not represented as Devashish's own-company hand audit.

## Checkpoint 1

- [ ] Confirm the Brightspace submission contains a commit permalink to the repository commit holding the desk, the Costco and Apple course runs, Devashish's Belden selected-company report, and any required reciprocal partner evidence. The Brightspace submission status has not been verified here.
- Repository visibility remains private per Devashish's instruction, although the course prerequisite specifies a public repository. Resolve that mismatch before relying on instructor access to the permalink.
