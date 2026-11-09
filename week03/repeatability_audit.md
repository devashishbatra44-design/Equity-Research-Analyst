# Week 3 repeatability audit

## Fixed graph result

| Run folder | Required graph order | Retry used | Core marks | Model definition findings |
|---|---|---|---:|---|
| `COSTCO_WHOLESALE_CORP_NEW_COST_20261105_032842` | Steps → Research Analyst → Financial Analyst → Investment Advisor → Strategy Manager → Verifier | No | 11 Correct; 0 Wrong; 0 Unsupported | No non-correct finding |
| `COSTCO_WHOLESALE_CORP_NEW_COST_20261105_033041` | Steps → Research Analyst → Financial Analyst → Investment Advisor → Strategy Manager → Verifier | Financial Analyst once | 11 Correct; 0 Wrong; 0 Unsupported | No non-correct finding |

The retry is the fixed Manager repair slot.
No role ran more than twice.
The Verifier ran last in both runs.
The first run folder remained unchanged when the second run was created.

## Current remediated reports

| Run folder | Company | Deterministic result | External calls during reconciliation |
|---|---|---|---|
| `COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525_RECONCILED_20261109_151446` | Costco | 41 Correct; 0 non-correct | None |
| `NETFLIX_INC_NFLX_20261109_131548_RECONCILED_20261109_150520` | Netflix, Shivani Rathi's Week 2 partner pick | 43 Correct; 0 non-correct | None |

The fresh Netflix data run reads the 10-K short-term-debt line and calculates debt-to-equity.
Each derived folder preserves the original report and role outputs before reconciliation.
Netflix reported in October, so it does not satisfy the separate Lab 05 requirement for a November-reporting partner pick.

## Browser page check

The Streamlit page started on port 8517.
Its health endpoint returned `ok`.
The page accepts ticker, peers, closing price, price date, and price source.
It streams node names and displays the verified report.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built and tested the graph, verifier, and browser page. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
