Filings used: amended registration statement accession 0001104659-26-041977; final information statement accession 0001104659-26-060223; current report accession 0001104659-26-068519; annual report accession 0001628280-26-053359; quarterly report accession 0001628280-26-068246; saved ownership-report audit.

# FDXF Investor Worksheet

Run time: 2026-11-20, Eastern time.

Security: FedEx Freight Holding Company, Inc. (NYSE: FDXF).

This is an analytical worksheet. It is not a Buy, Hold, or Sell recommendation.

## Evidence

- The complete one-fact-per-line filing worksheet is saved in `facts.md`.
- The filing and hash manifest is saved in `source_manifest.md`.
- The approved market-data method is saved in `MARKET_DATA_METHOD.md`.
- Nasdaq is the primary close-and-volume source for this run.
- Capital IQ is an independent cross-check for the 2026-11-19 close.

## Key transaction facts

- Parent: FedEx Corporation. Source: final information statement, accession 0001104659-26-060223, The Spin-Off.
- Distribution ratio: one FDXF share per two FDX shares. Source: final information statement, accession 0001104659-26-060223, The Spin-Off, saved line 47.
- Record date: 2026-05-15. Source: final information statement, accession 0001104659-26-060223, Questions and Answers About the Spin-Off, saved line 396.
- Distribution date: 2026-06-01. Source: current report, accession 0001104659-26-068519, Item Two, saved lines 223-230.
- Shares distributed by FedEx: 80.1% of FDXF shares. Source: current report, accession 0001104659-26-068519, Item Two, saved line 224.
- Stake initially retained by FedEx: 19.9% of FDXF shares. Source: final information statement, accession 0001104659-26-060223, The Spin-Off, saved line 47.
- Senior notes issued: 3.7 USD billions. Source: quarterly report, accession 0001628280-26-068246, Note Seven, saved lines 1216-1224.
- Term loan issued: 0.6 USD billions. Source: quarterly report, accession 0001628280-26-068246, Note Seven, saved lines 1218-1224.
- Cash paid to FedEx: approximately 4.1 USD billions. Source: current report, accession 0001104659-26-068519, Item Eight, saved lines 244-246.
- No qualifying officer or director transaction-code P purchase was found in the 34 ownership reports reviewed from 2026-06-01 through 2026-08-30. Source: `evidence/form4_f3_audit.json`, saved lines 238-285.

## Balance-sheet facts

- Funded debt fair value, excluding finance leases: approximately 4.0 USD billions at 2026-09-30. Source: quarterly report, accession 0001628280-26-068246, Note Seven, saved lines 1229-1235.
- Finance-lease liabilities: 255 USD millions at 2026-09-30. Source: quarterly report, accession 0001628280-26-068246, Note Seven, saved lines 1202-1204.
- Cash: 388 USD millions at 2026-09-30. Source: quarterly report, accession 0001628280-26-068246, Condensed Consolidated Balance Sheets, saved lines 111-115.
- Net pension liabilities: 22 USD millions at 2026-09-30. Source: quarterly report, accession 0001628280-26-068246, Note Ten, saved lines 1437-1439.
- Operating-lease liabilities: 1,841 USD millions at 2026-09-30. Source: quarterly report, accession 0001628280-26-068246, Condensed Consolidated Balance Sheets, saved lines 172-193.
- Transition Services Agreement expense: 30 USD millions for the four months ended 2026-09-30. Source: quarterly report, accession 0001628280-26-068246, Note Twelve, saved lines 1567-1572.
- Total recurring incremental standalone cost: not known. Sources: annual report, accession 0001628280-26-053359, Stand-Alone Company Expenses; quarterly report, accession 0001628280-26-068246, MD&A.

## Owner cash flow

- Reported net income: 655 USD millions for the fiscal year ended 2026-05-31. Source: annual report, accession 0001628280-26-053359, Consolidated Statements of Income, saved lines 1581-1587.
- One-time separation and other costs: 492 USD millions for the fiscal year ended 2026-05-31. Source: annual report, accession 0001628280-26-053359, MD&A, saved line 866.
- Effective tax rate: 25.9% for the fiscal year ended 2026-05-31. Source: annual report, accession 0001628280-26-053359, MD&A, saved lines 1037-1039.
- After-tax one-time-cost adjustment: 492 × (1 − 0.259) = 364.572 USD millions. Source: `calculations.json`.
- Adjusted after-tax earnings: 655 + 364.572 = 1,019.572 USD millions. Source: `calculations.json`.
- Depreciation and amortization: 449 USD millions for the fiscal year ended 2026-05-31. Source: annual report, accession 0001628280-26-053359, Consolidated Statements of Cash Flows, saved lines 1630-1634.
- Capital expenditures: 379 USD millions for the fiscal year ended 2026-05-31. Source: annual report, accession 0001628280-26-053359, Consolidated Statements of Cash Flows, saved lines 1697-1705.
- Owner cash flow: 1,019.572 + 449 − 379 = 1,089.572 USD millions. Source: `calculations.json`.

## Value range

- Primary diluted denominator: 149.9 million shares. Source: quarterly report, accession 0001628280-26-068246, Condensed Consolidated Statements of Income, saved lines 392-396.
- Severe-stress value at 10.00×: 72.69 USD per diluted share. Source: `calculations.json`.
- Approved low value at 14.00×: 101.76 USD per diluted share. Source: `calculations.json`.
- Approved mid value at 18.75×: 136.29 USD per diluted share. Source: `calculations.json`.
- Supplemental-high value at 28.00×: 203.52 USD per diluted share. Source: `calculations.json`.
- Supplemental five-year DCF: not computed. Required forecast depreciation, capital expenditures, normalized working-capital investment, and terminal ROIC are not all supported.

## Persona judgment

The saved one-call judgment is in `persona_output.md`. It contains six unweighted criterion scores, the supported cheap case, the disconfirming case, and exactly one next-filing condition. The model did not calculate a financial number or decide liquidity or conviction.

## Liquidity added by code after the persona call

- Official close: 126.58 USD per share on 2026-11-19. Primary source: Nasdaq official historical endpoint. Cross-check: S&P Capital IQ licensed export.
- Observation window: 30 regular trading sessions from 2026-10-09 through 2026-11-19. Source: `official_close_volume_reader.json`.
- Median daily dollar volume: 149,976,756.72 USD per day. Source: `calculations.json` from the saved Nasdaq closes and volumes.
- Intended purchase: 500,000 USD. Source: frozen human worksheet configuration.
- Maximum approved purchase fraction: 5.00% of median daily dollar volume. Source: frozen human worksheet configuration.
- Required median daily dollar volume: 10,000,000 USD per day. Source: `calculations.json`.
- Intended purchase as a fraction of median daily dollar volume: 0.3334%. Source: `calculations.json`.
- Liquidity result: passes.

## Release view

- Deciding number: low-case value minus official close = 101.76 − 126.58 = negative 24.82 USD per share. Source: `calculations.json`.
- Price view: the approved low-case value is less than the official close.
- Valuation result: fails the frozen low-value test.
- Liquidity result: passes the frozen client-liquidity test.
- Conviction: low under the frozen code rule because the valuation test fails while all required conviction inputs are computed.

## Not known or not computed

- Total recurring incremental standalone operating cost: not known.
- Separately quantified employment-related liabilities assumed at separation: not known.
- Separately quantified legal-action liabilities assumed at separation: not known.
- Supplemental five-year DCF: not computed because required inputs are unsupported.
