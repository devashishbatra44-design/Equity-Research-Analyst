# Final-persona run audit — Netflix

This audit identifies what the saved graph produced. It does not edit `report.md`.

## Graph result

- Company: Netflix (`NFLX`), selected by Shivani Rathi.
- Saved run: `NETFLIX_INC_NFLX_20261109_180226`.
- Node order: Steps; Research Analyst; Financial Analyst; Investment Advisor; Strategy Manager; Research Analyst retry; Financial Analyst retry; Investment Advisor refresh; Verifier.
- The Manager used no role more than twice.
- The Verifier ran last.
- `post_generation_report_edits`: empty.
- `code_written_insight_fallbacks`: empty.
- Tavily request: none.
- Financial Datasets request: none.

## Final-persona evidence

- The Research Analyst scored business-model durability, retention or the primary KPI, organic growth, expansion-driven growth, competitive advantage, catalyst evidence, and moat risk.
- The Financial Analyst scored revenue-growth quality, operating-margin direction, cash conversion, return on average equity, debt capacity, financial flexibility, GAAP diluted-EPS quality, valuation support, and peer-definition consistency.
- The Investment Advisor stated Buy, one deciding number, one catalyst, one risk, one valuation limitation, and one measurable result that would change the recommendation.
- Each analyst output ended with an `Insight:` line written by that model role.
- Code did not write or replace an Insight.

## Deterministic verification

- Correct: 92.
- Unsupported: 9.
- Wrong: 0.
- Missing core claims: 0.

The nine Unsupported marks remain visible in `verified_report.md`.
They mainly arise from dense sentences whose final citation does not support every number on that sentence.
The report was not post-edited to remove them.

## Partner check

Shivani's two completed core-claim checks and one completed Insight-citation check are recorded in `week03/HUMAN_SIGNOFF.md`.
The checked values and source lines are unchanged in this final-persona report.

Netflix reported in October 2026, not November 2026.
The repository states that fact because Netflix is the company Shivani selected.

This is a learning exercise, not financial advice.

AI assistance: Purdue GenAI Studio generated the three analyst outputs inside the CrewAI graph. OpenAI Codex implemented and tested the graph and verifier. I verified the filing sources myself; the judgments are mine.

Any remaining errors are my own.
