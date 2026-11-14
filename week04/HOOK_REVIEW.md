# Week 4 Numeric Hook Review

Status: built and tested; not enabled

Hook file: `equity_research_crewai/src/equity_research_crewai/numeric_hook.py`

Test file: `equity_research_crewai/tests/test_numeric_hook.py`

## What it checks

- Every numeric token in the saved worksheet has a declared category.
- Filing facts carry a tag, period, units, form, accession, section, source, and saved line.
- The printed value occurs on the cited saved filing line.
- Printed arithmetic recomputes from the printed inputs.
- Human rates and weights match an external frozen configuration.
- A licensed price matches a saved closes-reader record.
- Unknown numeric categories fail.
- Only dates, accessions, and line numbers can use the ignored categories.

## Test behavior

- A clean structured worksheet returns with no output.
- An owner-cash-flow result changed by 1 fails.
- A missing numeric classification fails.
- A filing value that is absent from its cited line fails.
- A price that does not match the saved reader record fails.

The refusal starts with:

`REFUSE: saved worksheet numeric verification failed`

## Enablement gate

No `.codex/hooks.json`, `.codex/config.toml`, or Claude hook setting was added.

Devashish must inspect this file and the hook source before any Stop hook is enabled. Enabling a hook changes agent completion behavior and is outside this audit until that review is recorded.
