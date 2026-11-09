# Mastering AI for Finance — Equity Research Desk

This repository contains the FIN 67110 equity-research desk, its SEC data workflow, company reports, and manual audit records.

The Week 3 desk supports optional, source-bounded Tavily research through `--tavily`.
Tavily supplies supplementary qualitative context only.
SEC filings remain authoritative for audited financial claims.

## Course work

- Week 1 setup and learning notes: [week01/README.md](week01/README.md)
- Week 2 desk, readings, run status, and audit notes: [week02/README.md](week02/README.md)
- Week 3 fixed graph, Verifier proofs, personas, and run status: [week03/README.md](week03/README.md)
- Professor-provided FAskills course integration: [week03/FASKILLS_INTEGRATION.md](week03/FASKILLS_INTEGRATION.md)

## Local setup and verification

Run these commands from this repository. Activating this repository's environment prevents another project's Python environment from being used by mistake.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r week02/requirements.txt
PYTHONPATH=.:week01 python -m pytest -q
python -m pip check
```

Run the Week 1 environment check with:

```bash
python check_env.py
```

The command prints only a four-character key prefix and the SEC User-Agent. Never paste that output into a public file.

The ASD-STE100 rewrites of the Lab 02 and Lab 03 build requests are in [Prompt Library](Prompt%20Library/).

## Run the desk

Run the seven SEC data steps without model calls:

```bash
python week02/desk_steps.py TICKER --peers T1,T2,T3 --price PRICE --price-date YYYY-MM-DD --price-source SOURCE
```

Run the seven steps and the four model roles:

```bash
python week02/desk_app.py TICKER --peers T1,T2,T3 --price PRICE --price-date YYYY-MM-DD --price-source SOURCE
```

Use a closing price, date, and source that you verified before either command. The program creates a timestamped folder under `week02/runs/`. It saves filing provenance, XBRL facts, calculations, peer facts, role records, the Manager review, the report, and an audit worksheet there. The final reviewed folders also contain the public SEC filing text needed to check line citations. Licensed data remains local.

`report.md` is immutable desk output reconstructed from `role_outputs.json`. Human additions belong in `student_notes.md`. This separation lets a reader compare the desk’s output with the manual audit.

Check report provenance with:

```bash
python week02/report_provenance.py week02/runs/RUN_FOLDER
```

## Run the Week 3 agent team

The Week 3 implementation uses a fixed CrewAI Flow:

`Steps → Research Analyst → Financial Analyst → Investment Advisor → Strategy Manager → Verifier`

Code selects every node and the Verifier cannot be skipped.
Run the graph from the repository root:

```bash
PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.main TICKER \
  --peers T1,T2,T3 \
  --price PRICE \
  --price-date YYYY-MM-DD \
  --price-source "SOURCE"
```

Start the browser page with:

```bash
.venv/bin/python -m streamlit run equity_research_crewai/src/equity_research_crewai/ui.py
```

Final Week 3 generated proofs:

- [Final Costco FAskills and Tavily verified report](week03/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525/verified_report.md): fixed graph, all nine source-bounded lenses, 14 of 14 code marks Correct, and 14 of 14 model definition marks Correct.
- [Costco verified persona report](week03/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261105_085335/verified_report.md): 11 core claims and three Insights marked Correct.
- [Netflix verified partner-pick report](week03/runs/NETFLIX_INC_NFLX_20261105_090924/verified_report.md): 10 available core claims and three Insights marked Correct; debt-to-equity is marked Not in filings.
- [Seeded-EPS Verifier proof](week03/verification_tests/seeded_eps_error/verified_report.md): seeded `$21.76` marked Wrong and corrected to `$20.76`.

The final Costco correction reused the saved Tavily result. It made no new Tavily search request.

## Company runs

The Week 2 company sequence is recorded as follows: Costco is the professor-assigned baseline, Apple is the professor-assigned in-class transfer run, and Belden is Devashish's selected company. Netflix was chosen by my partner Shivani Rathi, and the saved Netflix desk run is my partner’s-pick report.

| Company | Purpose | Report | Manual audit |
|---|---|---|---|
| Costco (COST) | Professor-assigned Week 2 baseline with peers | [report](week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708/report.md) | [audit](week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708/manual_audit.md) |
| Apple (AAPL) | Professor-assigned in-class transfer run | [report](week02/runs/Apple_Inc_AAPL_20261102_184430/report.md) | [audit](week02/runs/Apple_Inc_AAPL_20261102_184430/manual_audit.md) |
| Belden (BDC) | Devashish's selected company | [report](week02/runs/BELDEN_INC_BDC_20261102_233949/report.md) | [audit](week02/runs/BELDEN_INC_BDC_20261102_233949/manual_audit.md) |
| Netflix (NFLX) | Chosen by my partner Shivani Rathi; my partner’s-pick report | [report](week02/runs/NETFLIX_INC_NFLX_20261102_202506/report.md) | [worksheet](week02/runs/NETFLIX_INC_NFLX_20261102_202506/manual_audit.md) |

## Submission and privacy

Checkpoint 1 uses the commit permalink already submitted in Brightspace.
The repository is kept private while work is in progress.
Before a checkpoint submission, make the repository public and verify the exact commit permalink while logged out.
Checkpoint 2 requires a commit permalink containing the agent team and the seeded-error Verifier marks.

Secrets and local environment files must stay out of version control. Do not upload `.env`, API keys, or licensed raw data.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex, CrewAI, and Purdue GenAI Studio. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
