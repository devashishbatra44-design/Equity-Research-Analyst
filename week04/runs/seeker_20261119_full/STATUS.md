# Full Seeker Census Status

Run date: November 19, 2026

Status: complete locally; not committed or pushed

## Completed scope

- Downloaded the SEC full-quarter Form 10 and CERT index from January 1, 2024 through November 19, 2026.
- Saved 5,199 indexed filing rows.
- Reduced the index to 237 distinct Form 10 registrants.
- Reviewed the latest Form 10 filing text for all 237 registrants.
- Resolved all filing retrieval errors after bounded retries.
- Identified 15 distributions from November 19, 2025 through November 19, 2026.
- Preserved Reverse Morris Trust transactions and non-traded distributions without estimating a price.
- Completed F1, F2, and F3 for all 15 in-window distributions.
- Used the filing-stated regular-way start date for F1. The audit did not use when-issued prices.
- Kept five F1 results missing where a valid standalone child and same-date parent comparison did not exist.
- Reviewed every eligible Form 4/4-A through the earlier of 90 calendar days after distribution or November 19, 2026.
- Rendered `Ranked`, `Watch`, `Dropped`, and `Data limits` from the frozen factors.
- Passed 122 repository tests on November 19, 2026.

## Final screen counts

- Ranked: 10.
- Watch: 9, including five distributed names with missing F1 and four registered or future names.
- Dropped: 1 filing-proven direct registration control.

The highest frozen-factor scores are:

- Mobility Global Inc.: 2 of 3 points.
- Versant Media Group, Inc.: 2 of 3 points.

These scores are screen outputs. They are not investment recommendations.

## Frozen-factor audit totals

- F1: 2 true, 8 false, and 5 missing.
- F2: 5 true, 10 false, and 0 missing.
- F3: 4 true, 11 false, and 0 missing.

## Saved outputs

- `report.md`: final course-format seeker screen.
- `evidence.md`: per-name filing, price, calculation, and Form 4 evidence.
- `registry.json`: complete in-window and future-watch registry.
- `official_close_f1_audit.json`: official first-regular-close audit.
- `f2_filing_evidence.json`: human-readable SEC evidence input for F2.
- `sec_f2_audit.json`: validated F2 output.
- `form4_f3_audit.json`: full eligible-window Form 4 audit.
- `sec_form10_cert_candidates.json`: complete SEC candidate index.
- `form10_text_screen.json`: latest-filing text screen for 237 registrants.

## Remaining Week 4 dependency

The seeker is complete. The Lab 07 worksheet cannot run until Devashish freezes:

- the client type and intended purchase size;
- the minimum liquidity rule;
- the historical owner-cash-flow period and unknown-cost treatment;
- the low and mid value rates or multiples;
- the price-to-low-value comparison rule;
- the high, low, and not-computed conviction rules; and
- all six parts of the investor persona.

No Git commit or push was made during this census work.
