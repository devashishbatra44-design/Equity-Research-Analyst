# Week 3 human sign-off

This file records only checks performed by a person.
Do not mark a row until the named person opens the cited filing evidence.

## Lab 04 seeded-EPS check

- Proof file: `verification_tests/seeded_eps_error/verified_report.md`.
- Seeded report value: `$21.76`.
- Verifier correction: `$20.76`.
- Filing evidence: Costco 10-K, accession `0000909832-26-000093`, diluted EPS line; saved source `10-k.txt:1294`.
- Partner mark: **Wrong**. The seeded `$21.76` differs from the filing value of `$20.76`.
- Partner name and initials: Shivani Rathi (`SR`).
- Check date: November 9, 2026.

## Netflix partner-company check completed by Shivani Rathi

- Generated report: `runs/NETFLIX_INC_NFLX_20261105_090924/report.md`.
- Verified report: `runs/NETFLIX_INC_NFLX_20261105_090924/verified_report.md`.
- Final-persona graph report using the same filing package: `runs/NETFLIX_INC_NFLX_20261109_180226/report.md`.
- Final-persona verified report: `runs/NETFLIX_INC_NFLX_20261109_180226/verified_report.md`.

### Insight citation

- Claim to check: Current-quarter operating margin was `34.6%`.
- Filing evidence: Netflix Exhibit 99.1, accession `0001065280-26-000290`; saved source `exhibit-99-1.txt:14`.
- Partner mark: **Correct**.

### Core claim 1

- Claim to check: Current-quarter total revenue was `$12,874,176,000`.
- Filing evidence: Netflix Exhibit 99.1, accession `0001065280-26-000290`; saved source `exhibit-99-1.txt:274-277` states that the table is in thousands and reports `12,874,176`.
- Partner mark: **Correct**.

### Core claim 2

- Claim to check: Current-quarter GAAP diluted EPS was `$0.87`.
- Filing evidence: Netflix Exhibit 99.1, accession `0001065280-26-000290`; saved source `exhibit-99-1.txt:289-291`.
- Partner mark: **Correct**.

- Partner name and initials: Shivani Rathi (`SR`).
- Check date: November 9, 2026.

Devashish confirmed that Shivani selected Netflix and completed these two core-claim checks and one Insight-citation check.
The final-persona run states the same three values from the same Netflix filing lines, so this file records those completed partner checks beside the final-persona artifact.
No mark is inferred for any other claim.

Netflix reported in October 2026, not November 2026.
The repository states that timing fact rather than relabeling the filing month.
Netflix remains the partner-selected company because Shivani selected it and Devashish confirmed that this selection cannot be changed.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex prepared and formatted this sign-off worksheet. Shivani Rathi performed the human checks. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
