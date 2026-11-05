# Week 3 persona design record

Devashish Batra wrote the original design, purpose, criteria, source boundaries, change conditions, output requirements, and quality checks for all three personas.
The professor permitted AI-assisted editing after the student supplied that design.
OpenAI Codex refined the wording and converted the design into operational role instructions.
Devashish remains responsible for the final judgments and source checks.

## Final personas

### Research Analyst

- Persona: Moat-Durability and Catalyst Analyst.
- Purpose: Determine whether the company's competitive position is strengthening or weakening.
- Source boundary: Supplied 10-K Business section, 10-K MD&A section, earnings release, filing identifiers, and exact source lines.
- Owned sections: `Overview`; `Market Positioning and Growth Outlook`; `Future Developments and Strategic Recommendations`.
- Final role file: `equity_research_crewai/src/equity_research_crewai/roles/research_analyst.md`.

### Financial Analyst

- Persona: Earnings-Quality and Cash-Conversion Analyst.
- Purpose: Test whether reported growth creates sustainable profit and cash.
- Source boundary: Supplied XBRL facts, code-calculated ratios, quarterly release facts, peer facts, documented price input, filing references, and exact source excerpts.
- Owned section: `Valuation Insights`.
- Final role file: `equity_research_crewai/src/equity_research_crewai/roles/financial_analyst.md`.

### Investment Advisor

- Persona: Asymmetric-Risk and Valuation Analyst.
- Purpose: Decide whether expected upside adequately compensates for valuation and downside risk.
- Source boundary: Research Analyst and Financial Analyst outputs only.
- Owned section: `Investment Recommendation`.
- Final role file: `equity_research_crewai/src/equity_research_crewai/roles/investment_advisor.md`.

## Shared operating rules

- Each persona uses the six required parts: Identity; How I read a company; What I am given; Criteria I score; What would change my view; Output.
- No persona names a company or includes a company-specific value.
- No role receives information outside the graph's JSON hand-off.
- Every reported number must carry its exact filing-line or code-calculation source.
- Every number in an `Insight:` line must have its own exact citation token immediately after the number.
- One citation must not support several numbers from different source lines.
- A role must remove a number when the supplied context has no exact citation for it.
- The final nonblank line of each role output begins exactly `Insight:`.
- An Insight must add an analytical relationship. It must not merely repeat the earnings release's first paragraph.
- The Manager remains a checklist in code. It does not receive a new investment persona.

## Team formation

- Student 1: Devashish Batra
- Student 2: [Name]
- Student 3: [Name]
- Team name: [Name]

This is a learning exercise, not financial advice.

AI assistance: Devashish Batra supplied the persona design; OpenAI Codex made editorial and operational updates with the professor's permission. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
