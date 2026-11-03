# Week 2 Completion Audit

Audit date: November 2, 2026.

This file records a repository and execution audit. It does not replace the student's required hand audit of financial claims.

## Verified locally

- Python 3.12.10 is available in the repository's `.venv`.
- `check_env.py` reads the local key and SEC User-Agent. The audit suppressed both values.
- `.env` is excluded by `.gitignore`.
- No likely real API key was found in tracked text.
- The desk code contains no hard-coded company name for COST, WMT, AAPL, BDC, or NFLX.
- The SEC client sends the configured User-Agent on every request.
- The SEC client limits requests to five per second.
- The SEC client uses a 30-second timeout.
- The SEC client retries HTTP 429 and 5xx responses up to three times.
- The SEC client stops with a clear message after HTTP 403.
- The Lab 02 and Lab 03 requests have separate ASD-STE100 rewrites in `Prompt Library`.
- Three Week 1 tests pass.
- Thirteen Week 2 tests pass.
- `pip check` reports no broken requirements.
- The main Python files compile.

## Lab 02 evidence

The final COST, WMT, AAPL, BDC, and NFLX data-run manifests report `success` for Steps 1 through 7.

The final WMT run reports:

- Total revenue: $713,163 million.
- Revenue tag: `us-gaap:Revenues`.
- Operating income: $29,825 million.
- Period end for both inputs: January 31, 2026.
- Operating margin: 4.1821%, calculated as 29,825 / 713,163.

The final COST, AAPL, BDC, and NFLX run folders contain filing metadata, XBRL facts, calculations, peer facts, and successful manifests. Downloaded filing text remains local and excluded from Git.

## Lab 03 evidence

The final COST, AAPL, BDC, and NFLX reports each contain all five required report sections.

Each final report names the filings and accession numbers on line 1.

Each final report gives the run time on line 2.

Each final Strategy Manager review reports `pass` with no requested retry.

The application uses separate calls for the Research Analyst, Financial Analyst, Investment Advisor, and Strategy Manager.

The application permits one section retry and stops if the second Strategy Manager review does not pass.

The Research Analyst now receives a bounded, line-labeled earnings-release excerpt instead of only the first 45 lines.

## Human-audit status

- COST: the student recorded all 11 core marks. Errors: 0. Missing: 0.
- AAPL: the student recorded all 11 core marks. Errors: 0. Missing: 0. Supplemental vendor forecasts and target prices are excluded from the Week 2 report.
- BDC: the student recorded all 11 core marks. Errors: 0. Missing: 0.
- NFLX: Netflix is Shivani Rathi's selected company. The blank local 11-claim worksheet is retained as reciprocal partner-review support and is not represented as Devashish's own-company audit.

Devashish reports that the reciprocal partner check is complete. Shivani's two checks of Devashish's Belden report are transcribed in the Belden audit worksheet.

## GitHub and submission status

- The GitHub repository is private at the time of this audit.
- The course instructions require a public repository for instructor access.
- The private `main` branch contains the desk, prompt rewrites, Costco and Apple course runs, Devashish's Belden run, and the reciprocal Netflix partner-review material.
- Local and remote `main` were verified to match after the private push.
- `.env`, downloaded filing text, licensed vendor files, and the licensed course-paper PDF are absent from the published commit contents.
- Brightspace submission status is not visible from this repository.
- The licensed Francis and Zhang paper PDF has been removed from Git tracking. The local file remains on the laptop.

## Items required before Checkpoint 1 is submission-ready

The local work, private commit, and private push are complete. Only these externally visible actions remain:

1. Change the repository to public only when Devashish authorizes that change.
2. Open the final commit permalink while logged out. Confirm that the required reports open and `.env` does not.
3. Submit that commit-specific permalink in Brightspace.

The public schedule still lists Checkpoint 1 on Session 3. Devashish reports that Brightspace changed the deadline to November 2, 2026. The Brightspace deadline should control if it records the instructor's private course update.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
