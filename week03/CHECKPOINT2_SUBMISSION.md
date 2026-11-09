# Checkpoint 2 — Verifier submission index

This page is the grading entry point for Checkpoint 2.
It links the fixed agent graph, the seeded-error known answer, the filing evidence, the human check, and the reproducible tests.

## Required result

The seeded report states annual GAAP diluted EPS of **$21.76**.
The Costco 10-K states annual GAAP diluted EPS of **$20.76**.
The Verifier marks the seeded claim **Wrong** and supplies the filing value of **$20.76**.

| Item | Evidence |
|---|---|
| Seeded report value | `$21.76` |
| Filing value | `$20.76` |
| Course mark | `Wrong` |
| Filing | Costco 10-K, accession `0000909832-26-000093` |
| Per-share line | [`verification_tests/seeded_eps_error/10-k.txt:1294`](verification_tests/seeded_eps_error/10-k.txt#L1294) |
| Verifier output | [`verification_tests/seeded_eps_error/verified_report.md`](verification_tests/seeded_eps_error/verified_report.md) |
| Human sign-off | [`HUMAN_SIGNOFF.md`](HUMAN_SIGNOFF.md) |

The first table in the verified report places the report value, filing value, course mark, and filing line beside each other.
The optional model definition review is not needed for this offline known-answer proof.
The deterministic code marks are the Checkpoint 2 evidence for exact values and arithmetic.

## Graph and Verifier controls

The graph order is fixed in code:

`Steps → Research Analyst → Financial Analyst → Investment Advisor → Strategy Manager → Verifier`

- Code selects the next node.
- The Verifier is the final node.
- No command-line option can skip the Verifier on a full run.
- Each node input and output is saved.
- The Manager may retry a failing analyst role once.
- Code does not delete a failed model claim or write a replacement `Insight:`.

The implementation is in [`equity_research_crewai`](../equity_research_crewai/).

## Known-answer coverage

The deterministic proof set is documented in [`verification_tests/README.md`](verification_tests/README.md).

- Clean report: every checked number is Correct.
- Seeded diluted-EPS error: `$21.76` is Wrong and corrected to `$20.76`.
- Invented growth error: the report's 14.14% is marked Wrong because the filing inputs produce approximately 10.14%.
- Web and uncited numbers: the added values are Unsupported.
- Correctly rounded growth: accepted as Correct when the cited inputs establish the arithmetic.
- Numeric labels such as “5-factor”: excluded from financial-claim testing.

## Reproduce the result

From the repository root:

```bash
source .venv/bin/activate
PYTHONPATH=.:week01 python -m pytest -q
python week03/create_verifier_proofs.py
```

Repository result at preparation: **73 tests passed**.
The proof generator asserts the required known answers and exits with an error if any proof fails.

## Submission status

- Repository and proof artifacts: complete.
- Secret-safety check: complete; `.env` and API keys are excluded.
- Public logged-out repository check: complete before submission.
- Brightspace Checkpoint 2 permalink: pending student submission.
- Brightspace receipt: pending student submission.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex implemented and tested the deterministic Verifier and organized this submission index. Purdue GenAI Studio generated analyst-role outputs in full graph runs. I verified the filing sources myself; the judgments are mine.

Any remaining errors are my own.
