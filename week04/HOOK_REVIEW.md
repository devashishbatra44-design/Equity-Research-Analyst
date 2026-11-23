# Week 4 Numeric Hook Review

Status: built, tested, enabled, and trusted

Hook file: `equity_research_crewai/src/equity_research_crewai/numeric_hook.py`

Test file: `equity_research_crewai/tests/test_numeric_hook.py`

## What it checks

- Every numeric token in the saved worksheet has a declared category.
- Filing facts carry a tag, period, units, form, accession, section, source, and saved line.
- The printed value occurs on the cited saved filing line.
- Printed arithmetic recomputes from the printed inputs.
- Human rates and weights match an external frozen configuration.
- An official-exchange or licensed price matches a saved closes-reader record.
- The trading-session count and median daily dollar volume recompute from the saved market records.
- Unknown numeric categories fail.
- Only dates, accessions, and line numbers can use the ignored categories.

## Test behavior

- A clean structured worksheet returns with no output.
- An owner-cash-flow result changed by 1 fails.
- A missing numeric classification fails.
- A filing value that is absent from its cited line fails.
- A price that does not match the saved reader record fails.
- The FDXF clean worksheet is silent.
- A copied worksheet output with course owner cash flow changed from 725 USD millions to 726 USD millions is refused.

The refusal starts with:

`REFUSE: saved worksheet numeric verification failed`

## Enablement record

- Devashish received the completed worksheet and hook-review links before enablement.
- Devashish approved local enablement on November 20, 2026.
- The project-only Stop hook is in `.codex/hooks.json`.
- The generic hook command is `week04/run_numeric_hook.sh`.
- Codex reported the hook as enabled and trusted at November 20, 2026 at 8:07:47 PM EST.
- The trusted hook is the repository-relative generic launcher recorded in `.codex/hooks.json`.
- The hook command uses a repository-relative path. It does not publish a local username or absolute path.
- The existing user-level Orca hooks were not changed.
- A seeded copy changed by 1 USD million caused exit code 2 and the required refusal. The original worksheet was not modified.
- The clean worksheet command exited with code 0 and no output.
