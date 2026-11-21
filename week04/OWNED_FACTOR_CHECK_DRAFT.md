# Owned Feature Draft — Spinoff Factor Validation

Status: approved and frozen on November 21, 2026

Human owner: Devashish Batra

Team: DJS Signal & Source Capital

## Purpose

Test whether the frozen F1, F2, and F3 screen factors identify stronger later price outcomes in the saved November 19, 2026 seeker universe.

The check will not convert the screen into an investment recommendation.

## Proposed pre-registration

- Freeze date: the date on which Devashish approves this complete design.
- Universe: the 10 names in the `Ranked` section of `runs/seeker_20261119_full/report.md`.
- Signal date: November 19, 2026.
- Entry price: the official regular close on November 19, 2026. If that close is unavailable, use the first official regular close after November 19 and disclose the substitution.
- Outcome: 90-calendar-day price return from the entry close to the first official regular close on or after February 17, 2027.
- Price source: Nasdaq official historical data when available. Preserve the saved raw response and normalized records.
- Dividend treatment: price return only. Do not label the result total return.
- F1 comparison: mean and median return for F1 true versus F1 false.
- F2 comparison: mean and median return for F2 true versus F2 false.
- F3 comparison: mean and median return for F3 true versus F3 false.
- Composite comparison: mean and median return for scores of 1 or more versus scores of 0.
- Planned comparisons: 4.
- Direction: the true or higher-score group must have the higher return for the comparison to agree with the screen.
- Missing-data rule: exclude a name only from the affected comparison. Count and print every exclusion.
- Statistics rule: report group sizes, means, medians, and direction. Do not claim statistical significance from this small sample.
- Change rule: after approval, preserve this file. Record any later change in a dated amendment. Do not rewrite the original design.

## Proposed output

The output will show:

1. The frozen design and file hash.
2. Every included ticker and its factor values.
3. The entry and ending prices with dates and sources.
4. The return arithmetic for each ticker.
5. Four comparison rows.
6. The number of included and excluded observations.
7. A limitation stating that one small 90-day sample cannot validate an investment strategy.

## Approval

Approval statement: Devashish Batra wrote `approved the above` on November 21, 2026.

The controlling machine-readable design is `OWNED_FACTOR_CHECK_FROZEN.json`. The baseline command can run now. Do not run the return test before the frozen outcome date.
