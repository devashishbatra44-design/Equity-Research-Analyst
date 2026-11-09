# FAskills methodology record

Source methodology: CinderZhang/FAskills financial-researcher v2.0.0.

The nine named frameworks are analytical lenses. They are not statements or recommendations by those investors.
The three FIN 67110 personas, five report sections, Strategy Manager, and final Verifier remain unchanged.

## DRIVER trace

| Stage | Action | Status |
|---|---|---|
| DISCOVER | Reused the saved SEC filing set, approved Financial Datasets cross-check, and saved Tavily research without a new external request. | complete |
| PROCESS | Reused the saved deterministic FAskills metrics and recalculated quarter growth in Python. | complete |
| REPRESENT | Routed the filing-bounded Buffett, Lynch, Wood, and Soros lenses to the Research Analyst. | complete |
| IMPLEMENT | Completed the Research Analyst call with four independently labeled FAskills lenses. | complete |
| REPRESENT | Routed the Graham, Dalio, Burry, Simons, and Shiller lenses plus approved deterministic metrics to the Financial Analyst. | complete |
| IMPLEMENT | Completed the Financial Analyst call with five independently labeled FAskills lenses. | complete |
| IMPLEMENT | Synthesized only the two source-bounded analyst outputs into the Investment Advisor section. | complete |
| VALIDATE | Checked five-section completeness, core claims, Insight citations, and all nine lens labels. | complete |
| EVOLVE | Applied the fixed Manager checklist, used no more than one retry per role, and compiled the five report sections. | complete |
| VALIDATE | Started the mandatory final Verifier on the compiled report and saved evidence. | complete |
| REFLECT | Saved the verified report, DRIVER trace, expert-lens coverage, limitations, and reusable methodology record. | complete |

## Expert-lens routing

| Lens | Course role | Status | Available metrics |
|---|---|---|---|
| Buffett lens | Research Analyst | active_with_metrics | owner_earnings, fcf_conversion, piotroski_f_score, dupont_5_factor |
| Graham lens | Financial Analyst | active_with_metrics | piotroski_f_score, altman_z_manufacturing, altman_z_nonmanufacturing |
| Lynch lens | Research Analyst | active_with_metrics | piotroski_f_score |
| Wood lens | Research Analyst | active_with_metrics | gross_profitability |
| Soros lens | Research Analyst | active_source_limited | None; source-limited review only |
| Dalio lens | Financial Analyst | active_with_metrics | altman_z_manufacturing, altman_z_nonmanufacturing, piotroski_f_score, fcf_conversion, dupont_5_factor |
| Burry lens | Financial Analyst | active_with_metrics | beneish_m_score, sloan_accrual_ratio, owner_earnings, fcf_conversion, piotroski_f_score |
| Simons lens | Financial Analyst | active_with_metrics | piotroski_f_score, dupont_5_factor, sloan_accrual_ratio, gross_profitability |
| Shiller lens | Financial Analyst | active_source_limited | None; source-limited review only |

## Generated-output coverage

- Research Analyst: complete = `true`; missing labels = None.
- Financial Analyst: complete = `true`; missing labels = None.
- All nine lenses visible: `true`.

## Boundaries

- Missing evidence remains unavailable.
- The program does not create automatic price targets.
- The program does not simulate investor holdings or intent.
- The program does not use confidence-weighted voting.
- Tavily results are supplementary web context. SEC filings remain authoritative for audited financial claims.
- The mandatory Verifier remains the final graph node.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex adapted the professor's FAskills methodology to the course graph. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
