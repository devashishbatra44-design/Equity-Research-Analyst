# Lab 04 verifier proofs

These folders are copies of the same reviewed saved run.
Each folder preserves the filing texts, saved facts, calculations, report, verifier input, verifier output, and verified report.

## Clean report

The code Verifier marked all 11 core claims Correct.
The model definition review added no non-correct mark.

## Seeded diluted-EPS error

The test changes annual diluted EPS from $20.76 to $21.76 in the copied report.
The code Verifier marked the claim Wrong and corrected it to $20.76.
The model definition review independently marked the claim Wrong and cited the saved XBRL fact.

## Invented revenue-growth error

The test adds an annual revenue-growth claim of 14.14%.
The two annual filing values produce approximately 10.14%.
The code Verifier and model definition review marked the invented claim Wrong.

Regenerate the folders with:

```bash
.venv/bin/python week03/create_verifier_proofs.py
```

The regeneration command performs the deterministic code checks.
Run `--verify-only` on each folder to add the configured model definition review.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built the verifier and generated the seeded test copies; Purdue GenAI Studio performed the saved definition reviews. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
