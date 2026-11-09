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

Each metric records its formula, inputs, components, period, currency, accession number, interpretation, and missing fields.
Missing inputs produce an unavailable result.

The integration also implements the full DRIVER orchestration pattern:

1. `DISCOVER`: collect the saved SEC run and the licensed annual-financials response.
2. `PROCESS`: calculate deterministic metrics in Python before any model call.
3. `REPRESENT`: route only the required evidence and analytical lenses to each course role.
4. `IMPLEMENT`: run the three required analyst personas and the Manager in the fixed graph.
5. `VALIDATE`: check report structure, all eleven course claims, lens labels, Insight citations, and filing support.
6. `EVOLVE`: use no more than one retry per role and preserve every independent lens finding.
7. `REFLECT`: save the verified report, JSON trace, Markdown methodology record, and limitations.

All nine FAskills frameworks are active as independent analytical lenses:

- Research Analyst: Buffett, Lynch, Wood, and Soros.
- Financial Analyst: Graham, Dalio, Burry, Simons, and Shiller.
- Investment Advisor: source-bounded synthesis of the two analyst outputs.

The labels name methodologies.
They do not represent statements, holdings, endorsements, or current recommendations from those investors.

## SEC cross-check

Before a metric can enter a report, the extension compares these Financial Datasets values with the saved SEC run:

1. Total revenue.
2. Operating income.
3. Net income.
4. GAAP diluted EPS.
5. The 10-K reporting period.
6. The 10-K accession number.

The sidecar sets `report_use_allowed` to `true` only when every check passes.

## Course boundaries

The extension does not replace the three student-designed analyst personas.
It does not add a graph node.
It does not remove the mandatory Verifier.
It does not generate simulated guru opinions, confidence-weighted votes, holdings intent, or automatic price targets.
Tavily is available as an optional supplementary layer through `--tavily`.
It is not required for the graded filing checks.
Its results cannot replace SEC evidence or support an audited financial number without primary-source confirmation.
The exact query, URLs, dates, and excerpts are saved in `tavily_research.json` and checked by the final Verifier when cited.
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
The second file contains the derived metrics and SEC cross-check that may be reviewed in the course repository.

The Financial Analyst may use an available metric only when the SEC cross-check approves the sidecar.
The report must cite the sidecar metric, period, and accession number.
An Insight using a supplemental metric must also cite its supporting local filing line.

## Final validation

The final controlled Costco run is `runs/COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525`.
It reused five saved Tavily results without a new search request.
All nine analytical lenses are present.
The final Verifier produced 14 Correct code marks and 14 Correct model definition marks, with no Wrong, Unsupported, or Missing mark.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex installed the professor's FAskills source and implemented a course-safe adaptation. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
