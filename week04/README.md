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
| Human chapter notes | Pending human work | `HUMAN_PREWORK.md` |
| Two hand-found Form 10 examples | Pending human work | `HUMAN_PREWORK.md` |
| Human factor file | Pending human work | `HUMAN_FACTORS.md` |
| Human worksheet config | Pending human work | `HUMAN_WORKSHEET_CONFIG.md` |
| Human investor persona | Pending human work | `HUMAN_INVESTOR_PERSONA.md` |
| Closes reader | Built in code; local package or export still required | `equity_research_crewai/src/equity_research_crewai/closes_reader.py` |
| Seeker skill | Built and synthetic-tested; real filing validation waits for human inputs | `.agents/skills/fin67110-spinoff-seeker/SKILL.md` and `REQUIREMENTS.md` |
| Worksheet skill | Built and synthetic-tested; real run waits for human config and persona | `.agents/skills/fin67110-investor-worksheet/SKILL.md` and `REQUIREMENTS.md` |
| Numeric hook | Built and seeded-error tested; not enabled | `equity_research_crewai/src/equity_research_crewai/numeric_hook.py` and `HOOK_REVIEW.md` |
| First live report | Pending team selection and an eligible filing | `TEAM_DECISIONS.md` |
| Live-record index | Ready for GitHub commit links | `LIVE_RECORD.md` |
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

1. Devashish completes the human-only fields in the 4 templates in this folder.
2. The team selects the Week 4 live filing.
3. Run the closes reader against one exchange-checked close.
4. Run the tested seeker on the two human-found examples and the frozen factors.
5. Run the tested worksheet on the saved seeker result.
6. Review the numeric hook. Enable it only after review.
7. Save the live report in `week04/runs/live/`.
8. Commit and push the report to the team GitHub repository within 24 hours of the EDGAR Accepted time.
9. Record the permanent commit link and commit timestamp in `LIVE_RECORD.md`.

Do not upload the weekly report separately to Brightspace. Starting with Checkpoint 3, the checkpoint submission lists the live record completed so far.

The weekly reports are not separately graded. They are a project gate. Missing 1 week has no cost. Missing 2 weeks prevents the top project tier.
