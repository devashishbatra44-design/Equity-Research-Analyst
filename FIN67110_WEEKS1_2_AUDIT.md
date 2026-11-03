# FIN 67110 Weeks 1–2 Completion Audit

Audit date: November 2, 2026.

Latest desk rerun: COST completed on November 2, 2026 in `week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708`. Four model calls ran and the Manager returned `pass`. The generic peer reader now recovers each issuer’s exact revenue line label from inline XBRL, including Target’s `Net sales`. Its report is unchanged desk output and its manual audit shows the report and filing values side by side.

Audit specification: `FIN67110_Weeks1-2_Agent_Prompt.md`, checked against the current course pages for Week 1, Lab 01, Week 2, Lab 02, Lab 03, the report audit, the data page, grading, and Week 3 prework.

The course site governs when the downloaded prompt differs from it.

## Specification differences

- The Lab 02 URL in the downloaded prompt is outdated. The current page is `week-02/lab-02-desk-on-one-page.html`.
- The downloaded prompt asks Git to hold filing text. The final reviewed folders now commit the public SEC text needed to resolve line citations. Licensed data remains excluded.
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
| A11 | GitHub remote and logged-out public access | PASS | The remote is `https://github.com/devashishbatra44-design/Equity-Research-Analyst.git`. The repository is public. Final logged-out access and the `.env` 404 are rechecked after the remediation commit is pushed. |

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
| B8 | COST and WMT runs | PASS | Final COST and WMT manifests show Steps 1–7 successful. Code and derived facts are committed. The current COST folder includes the public SEC text used by its citations. |
| B9 | Lab 02 check files with blank student marks | FIXED | `week02/checks/lab02_COST_20261031_191554.md` and `week02/checks/lab02_WMT_20261031_191931.md`. The mark columns remain blank. |
| B10 | Pytest coverage | FIXED | All 26 tests pass. The suite covers saved runs, debt-tag handling, exact inline-XBRL line labels, report provenance, Netflix quarter growth, and Costco fiscal-date comparison. A fresh clone skips the one text-dependent test only when its public SEC text is absent. |

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
| C7 | Report header, five sections and disclaimer | PASS | Final COST, Apple, Belden and Netflix reports have filing accessions on line 1, zoned run time on line 2, five exact headings, and the disclaimer. Each `report.md` is reconstructed exactly from its saved role outputs. Former additions are in `student_notes.md`. |
| C8 | Required company sequence | PASS | Costco is the professor baseline. Apple is the professor’s in-class transfer run. Belden is Devashish’s selected company. Netflix is Shivani Rathi’s selected company and appears only as reciprocal partner-review evidence for Devashish. |
| C9 | Fallback, if needed | PASS | No fallback was required because the saved runs succeeded. |
| C10 | Commit and push | PASS | The pre-audit work is pushed. This report and its safe fixes are included in the audit-completion commit on `main`. |

## D — Human audit

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| D1 | Audit the desk output, not hand-edited text | FIXED | All final reports match `role_outputs.json`. Former additions are preserved separately as student notes. |
| D2 | COST, Apple and Belden audit files | PASS | Each current worksheet has `Report said`, `Filing says`, source, and student-mark columns. The reports’ actual generated claims are audited. |
| D3 | Counts, 11 claims, other numbers, template and recommendation | PASS WITH DISCLOSED LIMITATION | All 11 core claims are marked correct. The corrected Costco run has no errors or missing claims. The Belden audit discloses one unsupported price source and the resulting recommendation limitation. |
| D4 | Reciprocal partner checks | PASS | Devashish checked Netflix FY2025 revenue and Q3 2026 revenue. Shivani checked Belden FY2025 revenue and Q3 2026 revenue. Each check is one core claim and uses `Correct`, not `PASS`. Shivani’s marks are identified as transcribed from her message. |

## E — Checkpoint 1

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| E1 | Final public commit permalink in Brightspace | NEEDS ME | Devashish must confirm whether Brightspace already holds a permalink. The repository must be public when the instructor checks it. A final permalink will be produced after this audit commit is pushed. |

## F — Session 4 prework

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| F1 | Student audits 11 claims first | PASS | Devashish’s Costco 11-claim audit is complete and now shows each generated report value beside the filing value. |
| F2 | Fix only the role that erred, or the Financial Analyst if no error | FIXED | `week02/roles/financial_analyst.md` now contains the required source and no-estimation rules. Other role logic was not substantively changed. |
| F3 | Rerun COST into a new folder and save every source | PASS | The current corrected run is `week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708`; four role calls, no retries, Manager pass. `role_records.json`, the unedited report, audit worksheet, filing text and metadata, facts, calculations, and exact peer denominator labels were saved. |
| F4 | Inspect Manager code and write the one-line answer | PASS | Student's answer: “The code decides which role runs next; the Manager model can request a retry, but the code validates and executes at most one.” This matches `week02/desk_app.py`: `manager_review()` validates the returned sections, and `main()` maps and executes at most one retry per failing section before a post-retry review. |

## G — Polish

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| G1 | README with setup, run commands, outputs and disclaimer | FIXED | Root `README.md`. |
| G2 | Optional `--price-date` | PASS | Both CLIs support `--price-date`; the app requires it and saves it beside P/E. |
| G3 | Save every role's JSON input and output | PASS | The current COST run produced `role_records.json` with each role's instruction file, JSON input and output. |

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
- Both reciprocal partner checks are recorded as `Correct`: Devashish checked Shivani's Netflix report; Shivani checked Devashish's Belden report. Netflix is Shivani's company, not Devashish's selected company.
- Confirm or submit the final Checkpoint 1 permalink in Brightspace.
- Write the reading answers, gap list, reflections, Kasparov process line, and framework choice. The Manager-control line is recorded at F4.
- Read Kasparov and the first page of the selected framework.
- Continue rewriting future lab requests in ASD-STE100.

Devashish previously reported that LSEG Workspace, WRDS and S&P Capital IQ registration and login are complete.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex. I verified the repository and command outputs; the human audit judgments remain Devashish's.

Any remaining errors are my own.
