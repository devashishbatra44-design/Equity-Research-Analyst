# Mastering AI for Finance — Equity Research Desk

This repository contains the FIN 67110 equity-research desk, its SEC data workflow, company reports, and manual audit records.

## Course work

- Week 1 setup and learning notes: [week01/README.md](week01/README.md)
- Week 2 desk, readings, run status, and audit notes: [week02/README.md](week02/README.md)

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

Use a closing price, date, and source that you verified before either command. The program creates a timestamped folder under `week02/runs/`. It saves filing provenance, XBRL facts, calculations, peer facts, role records, the Manager review, the report, and an audit worksheet there. Downloaded filing text remains local and is excluded from Git.

## Company runs

The Week 2 company sequence is recorded as follows: Costco is the professor-assigned baseline, Apple is the professor-assigned in-class transfer run, and Belden is Devashish's selected company. Netflix is Shivani Rathi's selected company. Netflix material in this repository is supporting reciprocal partner-review evidence; it is not Devashish's own-company run.

| Company | Purpose | Report | Manual audit |
|---|---|---|---|
| Costco (COST) | Professor-assigned Week 2 baseline with peers | [report](week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_223224/report.md) | [audit](week02/runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261102_223224/manual_audit.md) |
| Apple (AAPL) | Professor-assigned in-class transfer run | [report](week02/runs/Apple_Inc_AAPL_20261102_184430/report.md) | [audit](week02/runs/Apple_Inc_AAPL_20261102_184430/manual_audit.md) |
| Belden (BDC) | Devashish's selected company | [report](week02/runs/BELDEN_INC_BDC_20261102_191754/report.md) | [audit](week02/runs/BELDEN_INC_BDC_20261102_191754/manual_audit.md) |
| Netflix (NFLX) | Shivani Rathi's selected company; partner-review material | [report](week02/runs/NETFLIX_INC_NFLX_20261102_202506/report.md) | [worksheet](week02/runs/NETFLIX_INC_NFLX_20261102_202506/manual_audit.md) |

## Submission and privacy

Checkpoint 1 uses a commit permalink submitted in Brightspace. The repository is public, and its final commit permalink is accessible while logged out. Confirm that Brightspace contains the final permalink and retain the submission receipt.

Secrets and local environment files must stay out of version control. Do not upload `.env`, API keys, or licensed raw data.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex and Purdue GenAI Studio. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
