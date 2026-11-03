# FIN 67110 Weeks 1–2 Completion Audit

Audit date: November 2, 2026.

Latest rerun: COST completed at 2026-11-02 22:33 local time in `week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_223224`. Four model calls ran, the Manager returned `pass`, and no retries were needed. The report now includes the previously missing same-quarter revenue growth: `(95,723 - 86,156) / 86,156 = 11.1043%`, matched to the 16-week columns in Exhibit 99.1. The worksheet keeps human marks blank.

Audit specification: `FIN67110_Weeks1-2_Agent_Prompt.md`, checked against the current course pages for Week 1, Lab 01, Week 2, Lab 02, Lab 03, the report audit, the data page, grading, and Week 3 prework.

The course site governs when the downloaded prompt differs from it.

## Specification differences

- The Lab 02 URL in the downloaded prompt is outdated. The current page is `week-02/lab-02-desk-on-one-page.html`.
- The downloaded prompt asks Git to hold filing text. The current Week 2 page asks for the code and saved folders' facts. This repository commits derived facts and provenance. It excludes downloaded filing text and licensed data.
- The downloaded prompt adds pytest, separate role files, machine-check Markdown files, and complete role-call records. These are useful polish requirements. The published Lab 02 and Lab 03 requests do not require their exact file layout.
- The grading page states that Checkpoint 1 is due on the day of Session 3. Devashish reports that Brightspace changed the date to November 2, 2026. Brightspace controls a private course update.

## A — Setup and safety

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| A1 | Python 3.11 or later | PASS | `python --version` and `.venv/bin/python --version` both printed Python 3.12.10. |
| A2 | `.gitignore` excludes `.env` | PASS | `git check-ignore -v .env` matched `.gitignore:2`. |
| A3 | `.env` absent from Git and history | PASS | `git ls-files .env` and `git log --all --oneline -- .env` printed nothing. |
| A4 | No key in tracked files or commits | PASS | Current and all-history key-pattern scans found no credential pattern. Non-placeholder `API_KEY` candidates were fake values in tests only. No secret value was printed. |
| A5 | A provider API key is stored locally and works | PASS | Purdue GenAI Studio key is configured as `GENAI_API_KEY`; `check_env.py` masked it, and the approved four-role run succeeded. It is never stored in chat or Git. |
| A6 | `check_env.py` masks the key and prints the User-Agent | PASS | It printed four key characters plus `...`, then `Devashish Batra batra44@purdue.edu`. |
| A7 | `hello.md` has date and model | PASS | `hello.md` records October 26, 2026 and OpenAI Codex. |
| A8 | Codex and Antigravity instruction files contain the ASD-STE100 line | FIXED | `AGENTS.md` already contained the exact line. `GEMINI.md` was added for Antigravity. |
| A9 | Placeholder-only `.env.example` | FIXED | `.env.example` now includes `API_KEY=paste-here` and `SEC_USER_AGENT="Your Name your@purdue.edu"`, plus placeholder Purdue GenAI settings. |
| A10 | Requirements and install command | FIXED | `week02/requirements.txt` lists Beautiful Soup, OpenAI, pytest, python-dotenv, and Requests. Install with `python -m pip install -r week02/requirements.txt`. |
| A11 | GitHub remote and logged-out public access | NEEDS ME | The remote is `https://github.com/devashishbatra44-design/Equity-Research-Analyst.git`. The temporary public test passed and `.env` returned 404. The repository is private now by Devashish's instruction. |

## B — Seven data steps

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| B0 | CLI supports ticker, peers, price and one step | PASS | `python week02/desk_steps.py --help`; no company name appears in production desk or role files. |
| B1 | Ticker to padded CIK | FIXED | `resolve_ticker`; class tickers now treat dot and dash separators as equivalent. |
| B2 | Exact 10-K, 10-Q and Item 2.02 8-K with Accepted times | FIXED | `select_filings`; future runs print newer amendments and skipped non-earnings 8-Ks and record the submissions/index time match. Saved COST and WMT filing files carry index URLs and Accepted times. |
| B3 | Download primary documents and Exhibit 99.1 | FIXED | `download_documents`; exact `EX-99.1` is preferred, with `EX-99.01` and `EX-99` supported as labeled fallbacks. Table rows remain on one line. |
| B4 | Latest-year XBRL facts with aligned periods and definitions | FIXED | Annual duration is restricted to 350–380 days. The run stops if the fact year differs from the latest 10-K report date. Revenue ties use the larger total-revenue value. Attributable net income and company-only equity no longer fall back to concepts that include noncontrolling interests. |
| B5 | Ratios computed in code with arithmetic | PASS | `calculate_measures`; saved calculations include inputs, periods, arithmetic and results. The published Lab 02 Step 5 does not require quarter growth; Lab 03 code computes it from release columns. |
| B6 | Exact quarter revenue and GAAP diluted-EPS lines | PASS | `extract_release_claims`; saved COST and WMT manifests record both claims as found. Adjusted EPS receives a lower selection score. |
| B7 | Peer facts from each peer's latest 10-K | FIXED | `process_peers`; future runs stop a peer when its XBRL period differs from its latest 10-K report date. Saved peer tables include company, period, tags, accession and one margin definition. |
| B8 | COST and WMT runs | PASS | Final COST and WMT manifests show Steps 1–7 successful. Code and derived facts are committed. Raw filing text remains local, as the current Week 2 page permits. |
| B9 | Lab 02 check files with blank student marks | FIXED | `week02/checks/lab02_COST_20261031_191554.md` and `week02/checks/lab02_WMT_20261031_191931.md`. The mark columns remain blank. |
| B10 | Pytest coverage | FIXED | `tests/test_week02_saved_runs.py` and existing tests. `PYTHONPATH=. .venv/bin/pytest -q` passes 21 tests, including Netflix quarter growth and Costco fiscal-date comparison. |

## C — Four-role app

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| C0 | Official provider SDK and local key | PASS | `week02/desk_app.py` uses the official OpenAI Python SDK against Purdue's OpenAI-compatible endpoint. It reads only local environment variables. |
| C1 | Four role calls with separate instructions | FIXED | Four files under `week02/roles/`; `load_role_instructions()` loads them. |
| C2 | JSON handoffs with limited role context | PASS | `json_handoff()` and the role-specific contexts in `desk_app.py`. |
| C3 | Research Analyst uses Business, MD&A and release lines | PASS | `research_analyst.md` and `extract_filing_sections()`. |
| C4 | Financial Analyst states and sources all core claims | FIXED | `financial_analyst.md` requires every source, exact tag or line, arithmetic, definitions, and `not stated in the filings` instead of an estimate. Code appends filing-based quantitative source notes. |
| C5 | Investment Advisor uses only analyst outputs | PASS | `advisor_context` contains only the two analyst outputs. |
| C6 | Manager checks five sections and permits one retry | PASS | `HEADINGS`, `assemble_report()`, `manager_review()`, `role_for_section()`, and the single retry block. Code fixes the initial order and caps the retry. The Manager model identifies a failing section within the allowed set. |
| C7 | Report header, five sections and disclaimer | PASS | Final COST, Apple, Belden and Netflix reports have filing accessions on line 1, zoned run time on line 2, five exact headings, and the disclaimer. |
| C8 | COST and partner-picked run | PASS | The latest COST report and the partner-picked NFLX report both exist. Netflix's full hand audit remains in D2. |
| C9 | Fallback, if needed | PASS | No fallback was required because the saved runs succeeded. |
| C10 | Commit and push | PASS | The pre-audit work is pushed. This report and its safe fixes are included in the audit-completion commit on `main`. |

## D — Human audit

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| D1 | Preserve existing human marks | PASS | This rerun did not change any existing financial mark or count. |
| D2 | COST and partner-pick audit files | PASS | Costco's 11-claim hand audit is complete, and Apple and Belden audit marks are present. The corrected COST run carries forward the same previously checked values and sources; its quarter-growth result is now explicit. |
| D3 | Counts, 11 claims, other numbers, template and recommendation | PASS | Costco, Apple and Belden audit worksheets contain the student's hand marks, error/missing counts, extra Financial Analyst checks, template and recommendation checks. |
| D4 | Reciprocal partner checks | PASS | Devashish checked two claims in Shivani Rathi's Netflix report (`week02/runs/NETFLIX_INC_NFLX_20261102_202506/manual_audit.md`), and Shivani checked two claims in Devashish's Belden report (`week02/runs/BELDEN_INC_BDC_20261102_191754/manual_audit.md`). Netflix is Shivani's company, not Devashish's selected company. Both marks are recorded as PASS. |

## E — Checkpoint 1

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| E1 | Final public commit permalink in Brightspace | NEEDS ME | Devashish must confirm whether Brightspace already holds a permalink. The repository must be public when the instructor checks it. A final permalink will be produced after this audit commit is pushed. |

## F — Session 4 prework

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| F1 | Student audits 11 claims first | PASS | Devashish's Costco 11-claim audit is complete. The new COST worksheet carries forward the same previously checked financial values and the matching 11.1043% quarter-growth calculation. |
| F2 | Fix only the role that erred, or the Financial Analyst if no error | FIXED | `week02/roles/financial_analyst.md` now contains the required source and no-estimation rules. Other role logic was not substantively changed. |
| F3 | Rerun COST into a new folder and save every source | PASS | Devashish approved the single rerun. It completed in `week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_223224`; four role calls, no retries, Manager pass. `role_records.json`, the report, audit worksheet, filings metadata, facts and calculations were saved. The quarterly-growth parser now matches the fiscal comparison columns. |
| F4 | Inspect Manager code and write the one-line answer | NEEDS ME | The relevant code is `week02/desk_app.py` at `main()`, `manager_review()`, and the retry block. Devashish must write his own one-line answer. |

## G — Polish

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| G1 | README with setup, run commands, outputs and disclaimer | FIXED | Root `README.md`. |
| G2 | Optional `--price-date` | PASS | Both CLIs support `--price-date`; the app requires it and saves it beside P/E. |
| G3 | Save every role's JSON input and output | PASS | The approved COST run produced `role_records.json` with each role's instruction file, JSON input and output. |

## Exact commands

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r week02/requirements.txt
```

Run the data steps only:

```bash
python week02/desk_steps.py TICKER --peers T1,T2,T3 --price PRICE --price-date YYYY-MM-DD --price-source SOURCE
```

Run the full desk. This makes paid model calls and requires approval first:

```bash
python week02/desk_app.py TICKER --peers T1,T2,T3 --price PRICE --price-date YYYY-MM-DD --price-source SOURCE
```

## Items only Devashish can complete or confirm

- Add the existing provider key manually as `API_KEY` in `.env` if exact prompt compliance is required. Do not paste it into chat.
- Keep or change GitHub visibility. The course requires public instructor access.
- Confirm the Lab 01 partner initials and Session 1 Brightspace checkout.
- Confirm the Lab 02 hand marks and the partner's two checks.
- Both reciprocal partner checks are recorded as PASS: Devashish checked Shivani's Netflix report; Shivani checked Devashish's Belden report. Netflix is Shivani's company, not Devashish's selected company.
- Confirm or submit the final Checkpoint 1 permalink in Brightspace.
- Write the reading answers, gap list, reflections, Kasparov process line, Manager-control line, and framework choice.
- Read Kasparov and the first page of the selected framework.
- Continue rewriting future lab requests in ASD-STE100.

Devashish previously reported that LSEG Workspace, WRDS and S&P Capital IQ registration and login are complete.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex. I verified the repository and command outputs; the human audit judgments remain Devashish's.

Any remaining errors are my own.
