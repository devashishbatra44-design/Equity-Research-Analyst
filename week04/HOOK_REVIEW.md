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
- A temporary FDXF close changed from 126.58 USD to 127.58 USD fails and names worksheet line 68.

The refusal starts with:

`REFUSE: saved worksheet numeric verification failed`

## Enablement record

- Devashish received the completed worksheet and hook-review links before enablement.
- Devashish approved local enablement on November 20, 2026.
- The project-only Stop hook is in `.codex/hooks.json`.
- The hook command is `week04/run_fdxf_numeric_hook.sh`.
- Codex reported the hook as enabled and trusted at November 20, 2026 at 8:07:47 PM EST.
- Trusted hook hash: `sha256:a14e1dfd8da75a318ef2e63fd84846a0e24b8380b4a18c70696157051cc3dfea`.
- The hook command uses a repository-relative path. It does not publish a local username or absolute path.
- The existing user-level Orca hooks were not changed.
- A temporary close changed by 1 USD caused exit code 2 and the required refusal.
- The value was restored to 126.58 USD, and the enabled hook command then exited with code 0 and no output.
