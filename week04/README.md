# Week 4 Control Record

Audited: November 14, 2026

Course window: November 9-15, 2026

Sessions: Lab 06 on November 10 and Lab 07 on November 12

This folder controls the Week 4 work. The current course pages govern if this record differs from the course site.

## Team

Team name: DJS Signal & Source Capital

- Devashish Batra
- Kuan-Jie Liao (Jason)
- Shivani Rathi
- Jeenay Vipul Dedhia

The public project page describes 3-student teams. Devashish confirms that Professor Zhang permitted this 4-person team. The original instructor message or Brightspace record is not stored in this repository.

## Week 4 mission

Build two reusable skills.

1. The seeker finds U.S. spinoffs with SEC filings, assigns a stage, reads a closing price, and ranks only declared factors.
2. The worksheet turns one saved screen result into a filing-sourced value range and a human-defined investor judgment.

The numeric hook must block completion when a financial number lacks a permitted source or a printed computation.

## Status

| Work item | Status | Evidence or next action |
|---|---|---|
| Week 4 page audit | Complete | `LINK_AUDIT.md` |
| Lab 06 contract | Complete | `REQUIREMENTS.md` |
| Lab 07 contract | Complete | `REQUIREMENTS.md` |
| Request samples | Complete | `LINK_AUDIT.md` |
| Instructor live-report clarification | Recorded and applied | `INSTRUCTOR_CLARIFICATION.md` |
| Data and licensing rules | Complete | `LINK_AUDIT.md` and `REQUIREMENTS.md` |
| Required reading map | Complete | `LINK_AUDIT.md` |
| Human chapter notes | Complete and approved by Devashish | `HUMAN_PREWORK.md` |
| Two hand-found Form 10 examples | Complete and approved by Devashish | `HUMAN_PREWORK.md` |
| Human factor file | Frozen before the first pre-registered run | `HUMAN_FACTORS.md` |
| Human worksheet config | Frozen and approved by Devashish | `HUMAN_WORKSHEET_CONFIG.md` |
| Human investor persona | Frozen and approved by Devashish | `HUMAN_INVESTOR_PERSONA.md` |
| Closes reader | Built in code; local package or export still required | `equity_research_crewai/src/equity_research_crewai/closes_reader.py` |
| Seeker skill | Complete locally; 15 in-window distributions audited for F1, F2, and F3; final report has 10 ranked, 9 watch, and 1 dropped row | `.agents/skills/fin67110-spinoff-seeker/SKILL.md`, `REQUIREMENTS.md`, and `runs/seeker_20261119_full/` |
| Worksheet skill | Built, synthetic-tested, and run on FDXF with saved SEC and Nasdaq evidence | `.agents/skills/fin67110-investor-worksheet/SKILL.md`, `REQUIREMENTS.md`, and `runs/worksheet_FDXF_20261120_023851/` |
| Numeric hook | Built, seeded-error tested, enabled, and trusted as a project Stop hook | `.codex/hooks.json`, `week04/run_fdxf_numeric_hook.sh`, and `HOOK_REVIEW.md` |
| First live report | Complete and pushed within the 24-hour deadline for WFCF | `runs/live/WFCF_20261114_144628/` and `LIVE_RECORD.md` |
| Live-record index | Week 4 permanent commit link recorded | `LIVE_RECORD.md` |
| Owned product line | Pending team decision | `TEAM_DECISIONS.md` |

## Safety boundaries

- Keep LSEG, WRDS, and Capital IQ raw data outside Git and model prompts.
- Keep `LSEG_APP_KEY` only in `.env`.
- Do not estimate a missing filing fact.
- Mark a missing price or fact as `not available` or `not known`.
- Code computes every number before a model sees it.
- Keep the 3 student-designed analyst personas from Week 3.
- Keep the Strategy Manager checklist and the Verifier as mandatory controls.
- Treat a screen as a screen. Do not present it as a recommendation.
- Show the hook file and its seeded-error test before enabling it.

## Immediate sequence

1. Devashish reviews the completed FDXF worksheet.
2. Commit or push only after Devashish approves publication.

## Reproducible seeker commands

Run the deterministic seeker tests:

```bash
.venv/bin/python -m pytest \
  equity_research_crewai/tests/test_spinoff_seeker.py \
  equity_research_crewai/tests/test_sec_spinoff_discovery.py \
  equity_research_crewai/tests/test_sec_form10_text_screen.py \
  equity_research_crewai/tests/test_sec_form4_audit.py -q
```

Rebuild the SEC index, text screen, and F3 audit:

```bash
PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.sec_spinoff_discovery \
  --start 2024-01-01 --end 2026-11-19 \
  --output week04/runs/seeker_20261119_full/sec_form10_cert_candidates.json

PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.sec_form10_text_screen \
  --input week04/runs/seeker_20261119_full/sec_form10_cert_candidates.json \
  --output week04/runs/seeker_20261119_full/form10_text_screen.json

PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.sec_form4_audit \
  --registry week04/runs/seeker_20261119_full/registry.json \
  --output week04/runs/seeker_20261119_full/form4_f3_audit.json
```

Rebuild F1, validate F2, and render the final seeker report:

```bash
PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.official_close_f1_audit \
  --registry week04/runs/seeker_20261119_full/registry.json \
  --output week04/runs/seeker_20261119_full/official_close_f1_audit.json

PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.sec_f2_audit \
  --input week04/runs/seeker_20261119_full/f2_filing_evidence.json \
  --output week04/runs/seeker_20261119_full/sec_f2_audit.json

PYTHONPATH=equity_research_crewai/src .venv/bin/python -m equity_research_crewai.build_full_seeker_report \
  --registry week04/runs/seeker_20261119_full/registry.json \
  --f1 week04/runs/seeker_20261119_full/official_close_f1_audit.json \
  --f2 week04/runs/seeker_20261119_full/sec_f2_audit.json \
  --f3 week04/runs/seeker_20261119_full/form4_f3_audit.json \
  --human-factors week04/HUMAN_FACTORS.md \
  --report-output week04/runs/seeker_20261119_full/report.md \
  --evidence-output week04/runs/seeker_20261119_full/evidence.md
```

Do not upload the weekly report separately to Brightspace. Starting with Checkpoint 3, the checkpoint submission lists the live record completed so far.

The weekly reports are not separately graded. They are a project gate. Missing 1 week has no cost. Missing 2 weeks prevents the top project tier.
