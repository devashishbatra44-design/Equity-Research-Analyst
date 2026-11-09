# FAskills course integration

The professor's official [FAskills repository](https://github.com/CinderZhang/FAskills) is installed as a Codex skill.
The repository also contains a course-safe processing extension.

## What is implemented

The optional processor makes one authenticated request to the Financial Datasets combined annual-financials endpoint.
It saves the response locally without the API key.
The raw response is excluded from GitHub because it is licensed vendor data.
It calculates these measures in Python:

- Piotroski F-Score.
- Altman Z-Score for manufacturing companies.
- Altman Z-double-prime for non-manufacturing companies.
- Beneish M-Score.
- Conservative owner earnings.
- Five-factor DuPont decomposition.
- Sloan accrual ratio.
- Gross profitability.
- Free-cash-flow conversion.

Each review-only metric records its formula, inputs, components, period, currency, accession number, interpretation, and missing fields.
Missing inputs produce an unavailable result.
These vendor-derived values do not enter the graded report.

The integration also implements the full DRIVER orchestration pattern:

1. `DISCOVER`: collect the saved SEC run and the licensed annual-financials response.
2. `PROCESS`: calculate deterministic metrics in Python before any model call.
3. `REPRESENT`: route only SEC-derived evidence and analytical-lens definitions to each course role.
4. `IMPLEMENT`: run the three required analyst personas and the Manager in the fixed graph.
5. `VALIDATE`: check report structure, all eleven course claims, every other number outside the Advisor thesis, lens labels, Insight citations, and filing support.
6. `EVOLVE`: use no more than one retry per role and preserve every independent lens finding.
7. `REFLECT`: save the verified report, JSON trace, Markdown methodology record, and limitations.

All nine FAskills frameworks are active as independent analytical lenses:

- Research Analyst: Buffett, Lynch, Wood, and Soros.
- Financial Analyst: Graham, Dalio, Burry, Simons, and Shiller.
- Investment Advisor: source-bounded synthesis of the two analyst outputs.

The labels name methodologies.
They do not represent statements, holdings, endorsements, or current recommendations from those investors.

## SEC cross-check and report-use boundary

The extension compares these Financial Datasets values with the saved SEC run:

1. Total revenue.
2. Operating income.
3. Net income.
4. GAAP diluted EPS.
5. The 10-K reporting period.
6. The 10-K accession number.

This partial cross-check is not enough to reproduce Piotroski, Altman, Beneish, DuPont, or the other derived scores.
Inputs such as assets, liabilities, retained earnings, gross profit, and shares remain vendor-derived.
Therefore `report_use_allowed` is always `false`, and no vendor-derived score or value may enter the graded report until every input is computed from SEC XBRL or independently cross-checked.

## Course boundaries

The extension does not replace the three student-designed analyst personas.
It does not add a graph node.
It does not remove the mandatory Verifier.
It does not generate simulated guru opinions, confidence-weighted votes, holdings intent, or automatic price targets.
Tavily is available as an optional saved sidecar through `--tavily`.
It is not required for graded filing checks and is excluded from graded role hand-offs.
Its results cannot replace SEC evidence or support an audited claim.
The exact query, URLs, dates, and excerpts are saved in `tavily_research.json` for review.
Use `--reuse-tavily` with `--saved-run` and `--tavily` to correct a saved report without spending another Tavily credit.

## Command

```bash
.venv/bin/python -m equity_research_crewai.main TICKER \
  --saved-run week02/runs/SAVED_RUN_FOLDER \
  --faskills
```

The command writes these files in the new Week 3 run folder:

- `faskills_financialdatasets.json`.
- `faskills_metrics.json`.
- `faskills_methodology.json`.
- `faskills_driver_trace.json`.
- `faskills_methodology.md`.

The first file remains local.
The second file contains review-only derived metrics and the partial SEC cross-check.

The Financial Analyst receives a block notice instead of vendor metric values.
An Insight must use SEC filing evidence or a deterministic calculation built from SEC facts.

## Final validation

The original controlled Costco run is `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525`.
Its corrected derivative is `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525_RECONCILED_20261109_151446`.
The derivative preserves the original output, removes unsupported numerical lines fail-closed, strips blocked vendor citations, and makes no model, Tavily, or vendor request.
The final deterministic Verifier produced 41 Correct marks, with no Wrong, Unsupported, or Missing mark.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex installed the professor's FAskills source and implemented a course-safe adaptation. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
