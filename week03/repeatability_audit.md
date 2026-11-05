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

## Lab 05 persona proof

| Run folder | Company | Core result | Insight result | Manager result |
|---|---|---|---|---|
| `COSTCO_WHOLESALE_CORP_NEW_COST_20261105_085335` | Costco | 11 Correct | 3 Correct | Pass; no unresolved issue |
| `NETFLIX_INC_NFLX_20261105_090924` | Netflix, chosen by partner Shivani Rathi | 10 Correct; 1 Not in filings | 3 Correct | Pass; no unresolved issue |

Netflix debt-to-equity is not calculated because the supplied filing facts do not state the current portion of long-term debt.
The desk does not replace that missing input with zero.

## Browser page check

The Streamlit page started on port 8517.
Its health endpoint returned `ok`.
The page accepts ticker, peers, closing price, price date, and price source.
It streams node names and displays the verified report.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built and tested the graph, verifier, and browser page. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
