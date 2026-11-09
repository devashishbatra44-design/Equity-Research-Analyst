# Lab 04 verifier proofs

These folders are copies of the same reviewed saved run.
Each folder preserves the filing texts, saved facts, calculations, report, verifier input, verifier output, and verified report.

## Clean report

The deterministic Verifier checked all 41 numerical claims outside the Advisor thesis and marked all 41 Correct.

## Seeded diluted-EPS error

The test changes annual diluted EPS from $20.76 to $21.76 in the copied report.
The deterministic Verifier marked the claim Wrong and corrected it to $20.76.
Its evidence includes the saved 10-K per-share line at `10-k.txt:1294`.

## Invented revenue-growth error

The test adds an annual revenue-growth claim of 14.14%.
The two annual filing values produce approximately 10.14%.
The deterministic Verifier marked the invented claim Wrong.

## Web and unsourced numbers

The test adds three web-sourced numbers and one number with no citation outside the Advisor's thesis.
The deterministic Verifier marks every added number Unsupported.
This proves that a plausible number does not pass merely because it appears in prose or behind a web link.

Regenerate the folders with:

```bash
.venv/bin/python week03/create_verifier_proofs.py
```

The regeneration command performs the deterministic code checks for all four reports.
Run `--verify-only` on a folder only when a separate model definition review is needed; the exact-value code marks remain authoritative.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built the verifier and generated the seeded test copies; Purdue GenAI Studio performed the saved definition reviews. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
