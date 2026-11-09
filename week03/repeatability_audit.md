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

## Honest graph-output review

| Run folder | Company | Deterministic result | Report edited after graph? |
|---|---|---|---|
| `COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525` | Costco | 67 Correct; 144 Unsupported | No |
| `NETFLIX_INC_NFLX_20261109_131548` | Netflix, Shivani Rathi's Week 2 partner pick | 42 Correct; 1 Unsupported | No |

The fresh Netflix data run reads the 10-K short-term-debt line and calculates debt-to-equity.
The verifier output shows unresolved claims instead of deleting them. Code never writes an Insight.
The old `RECONCILED` folders are historical post-processing diagnostics and are not the desk's output.
Netflix reported in October, so it does not satisfy the separate Lab 05 requirement for a November-reporting partner pick.

## Browser page check

The Streamlit page started on port 8517.
Its health endpoint returned `ok`.
The page accepts ticker, peers, closing price, price date, and price source.
It streams node names and displays the verified report.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built and tested the graph, verifier, and browser page. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
