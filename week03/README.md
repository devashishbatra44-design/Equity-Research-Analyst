# Week 3 — Your Agent Team

This folder tracks Week 3 against the current course instructions.

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
- [x] Clean, seeded-EPS, and invented-growth checks pass offline.
- [x] Run and save the three verifier proofs with the configured model.
- [x] Run the complete graph twice on the same ticker and retain both folders.
- [ ] Have the partner check the seeded-EPS mark against the 10-K.

## Lab 05 implementation

- [x] The browser page accepts ticker, peers, price, date, and source.
- [x] The page streams each node name.
- [x] The page displays the verified report and its marks.
- [x] The page starts successfully and passes its local health check.
- [x] The Manager code can require one final `Insight:` line from each analyst role once the three six-part personas are present.
- [x] The Manager rejects an Insight line with no filing-line citation or one sourced only to the release's first paragraph.
- [x] The Verifier compares numbers in each Insight line with its cited filing line.
- [x] Devashish supplied the three six-part persona designs; Codex made permitted editorial and operational updates.
- [x] Add the persona Insight checks after the student text is ready.
- [x] Run the full team on the partner's chosen company, Netflix.
- [ ] Partner checks two core claims and records both marks at the report top.
- [ ] Partner opens one Netflix Insight citation and confirms the filing line contains the claim.
- [ ] Record the three student names and team name.
- [ ] Push the final Week 3 artifacts.
- [ ] Submit a commit permalink to Brightspace Checkpoint 2.

## Repeatability proof

The two retained Costco runs are:

- `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261105_032842`
- `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261105_033041`

Both runs used the fixed order: Steps; Research Analyst; Financial Analyst; Investment Advisor; Strategy Manager; Verifier.
The second run used the one permitted Financial Analyst retry slot between the Manager and Verifier.
Each run has 11 of 11 deterministic core claims marked Correct.
Each model definition review has no non-correct finding.

## Lab 05 proof runs

- Final Costco persona run: `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261105_085335`.
- Final Netflix partner-pick run: `runs/NETFLIX_INC_NFLX_20261105_090924`.

The Costco run has 11 core claims and three Insights marked Correct.
The Netflix run has 10 available core claims and three Insights marked Correct.
Netflix debt-to-equity is marked `Not in filings` because the supplied facts do not state the current portion of long-term debt.
The Netflix run has no unresolved Manager issue and no role retry.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex helped build and test the graph, verifier, UI, and documentation. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
