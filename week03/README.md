# Week 3 — Your Agent Team

This folder tracks Week 3 against the current course instructions.
The optional professor-provided FAskills methodology is documented in [FASKILLS_INTEGRATION.md](FASKILLS_INTEGRATION.md).
It implements DRIVER and all nine expert frameworks as source-bounded lenses without changing the fixed course graph.

## Prework completed in code

- Checkpoint 1 was filed.
- The Week 2 Financial Analyst instruction requires a source for every number.
- It requires the phrase "not stated in the filings" instead of an estimate.
- The selected framework is CrewAI Flow.
- The fixed graph is implemented in `equity_research_crewai`.

## One-line answers

**What was the process in the Lab 03 desk?**
The process was the code-controlled sequence that ran the filings steps, three analyst roles, the Manager checklist, one allowed retry, and the saved outputs.

**Who decided which role ran next in Lab 03?**
Code decided which role ran next; the model wrote the content inside each role call.

**Which workflow is the Manager, and which is the Verifier?**
The Manager is the orchestrator-workers workflow; the Verifier is the evaluator-optimizer workflow.

**What does the Verifier receive?**
The Verifier receives only the compiled report, saved facts, and the cited lines retrieved from the saved filing texts.

**What does the Verifier never receive?**
The Verifier never receives the analyst roles' instruction files.

**Why would role instructions weaken the Verifier?**
They could bias the Verifier toward the role's intended reasoning instead of the filing evidence.

**What can the Verifier not catch by design?**
It cannot decide whether a true sourced number answers the client's intended question, and it cannot verify the Investment Advisor's thesis from a filing.

## Lab 04 implementation

- [x] CrewAI Flow project exists.
- [x] Structured state carries only explicit inputs and outputs.
- [x] Node order is fixed in code.
- [x] Each analyst role is a separate model call.
- [x] Each model role receives a JSON hand-off.
- [x] The Manager has one deterministic retry slot per failing role.
- [x] No role can run more than twice.
- [x] The Verifier runs after the Manager.
- [x] No CLI flag disables the Verifier.
- [x] `--verify-only` runs the Verifier and no other role.
- [x] Every node input and output is saved.
- [x] Clean, seeded-EPS, invented-growth, and web-plus-unsourced checks pass offline.
- [x] Save all four deterministic verifier proofs.
- [x] Run the complete graph twice on the same ticker and retain both folders.
- [x] Have the partner check the seeded-EPS mark against the 10-K.

## Lab 05 implementation

- [x] The browser page accepts ticker, peers, price, date, and source.
- [x] The page streams each node name.
- [x] The page displays the verified report and its marks.
- [x] The page starts successfully and passes its local health check.
- [x] The Manager code can require one final `Insight:` line from each analyst role once the three six-part personas are present.
- [x] The Manager rejects an Insight line with no filing-line citation or one sourced only to the release's first paragraph.
- [x] The Verifier compares numbers in each Insight line with its cited filing line.
- [x] Devashish supplied and committed the original three-persona design.
- [x] Keep operating rules separate from the student-authored persona identity, values, and criteria.
- [x] Add the persona Insight checks after the student text is ready.
- [x] Preserve the Week 2 Netflix partner-pick report and its completed human marks.
- [ ] Run Lab 05 on a new company that Shivani chooses and confirms reported in November 2026.
- [ ] Have Shivani check two core claims and one Insight citation in that new report.
- [x] Record the three student names.
- [x] Record the team name.
- [x] Push the Week 3 artifacts completed to date.
- [ ] Submit a commit permalink to Brightspace Checkpoint 2.

## Repeatability proof

The two retained Costco runs are:

- `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261105_032842`
- `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261105_033041`

Both runs used the fixed order: Steps; Research Analyst; Financial Analyst; Investment Advisor; Strategy Manager; Verifier.
The second run used the one permitted Financial Analyst retry slot between the Manager and Verifier.
Each run has 11 of 11 deterministic core claims marked Correct.
Each model definition review has no non-correct finding.

## Current graph-produced reports

- Costco: `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525`.
- Netflix: `runs/NETFLIX_INC_NFLX_20261109_131548`.

The Costco report has 67 Correct and 144 Unsupported deterministic marks. The Unsupported marks expose web, unreproduced vendor, and uncited numerical claims instead of deleting them.
The Netflix report has 42 Correct and one Unsupported deterministic mark. The failed Insight remains visible.
The fresh Netflix facts use the 10-K short-term-debt line, so debt-to-equity is calculated instead of marked unavailable.
Neither report was edited after the graph. The Verifier marks and filing corrections are appended to `verified_report.md`.
The old folders containing `RECONCILED` are historical post-processing diagnostics. They are not graph output and are not current proof runs.
Netflix remains Shivani Rathi's Week 2 partner pick; it does not satisfy the separate Lab 05 requirement for a company that reported in November.

## FAskills and Tavily boundary

- Original controlled run: `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525`.
- Fixed node order: Steps; Research Analyst; Financial Analyst; Investment Advisor; Strategy Manager; Verifier.
- FAskills methodology labels remain optional, but vendor-derived metric values are blocked from the graded report until every input is reproduced from SEC XBRL.
- Tavily results are saved as sidecars and excluded from graded role hand-offs.
- Current code marks on the unedited graph report: 67 Correct; 0 Wrong; 144 Unsupported; 0 Missing.
- Full repository result after the verifier correction: 71 tests passed.

The current verified graph artifact is [verified_report.md](runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525/verified_report.md).

## Team formation

- Student 1: Devashish Batra.
- Student 2: Kuan-Jie Liao.
- Student 3: Shivani Rathi.
- Team name: DJS Signal & Source Capital.
- DJS represents Devashish, Jason, and Shivani; Jason refers to Kuan-Jie Liao.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex helped build and test the graph, verifier, UI, and documentation. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
