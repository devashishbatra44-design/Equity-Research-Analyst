# Course operating rules

These are harness rules. They are not part of a role's identity, values, or scoring criteria.

- Use only the evidence included in the JSON hand-off.
- Put an exact filing-line citation or an exact `facts.json` citation immediately after every filing number.
- Put an exact `calculations.json` citation immediately after every code-calculated number.
- Do not use a web number in the graded report.
- Do not use a vendor-derived FAskills score in the graded report until every input is reproduced from SEC XBRL facts and the Verifier recomputes the score.
- Keep every period, condition, definition, and hedge supported by the source.
- Write `not stated in the supplied filings` when the supplied evidence does not state a value.
- Never calculate inside a model role.
- Preserve GAAP and adjusted labels.
- Name the denominator definition for every margin and peer comparison.
- In the Financial Analyst section, state the required claims with these exact lead phrases: `Annual total revenue was`; `Annual revenue growth was`; `Annual operating income was`; `Annual operating margin was`; `Annual net income attributable to the company was`; `Annual GAAP diluted EPS was`; `Return on average equity was`; `Debt to equity was`; `Free cash flow was`; `Quarter total revenue was`; `Quarter revenue growth was`; and `Quarter GAAP diluted EPS was`.
- Put each required claim on its own line. Do not add a second number to a required-claim line.
- Write citation tokens exactly, with no backticks and no space after the colon. Valid examples are `(10-k.txt:1294)`, `(facts.json:total_revenue)`, `(calculations.json:revenue_growth)`, `(peers.json:WMT:operating_margin)`, and `(manifest.json:price)`.
- Use one citation token for one source. Do not combine two source names inside one pair of parentheses.
- Do not write a numerical value unless its own exact citation token immediately follows it.
- Cite each peer operating margin as `(peers.json:TICKER:operating_margin)`.
- Cite the supplied share price as `(manifest.json:price)`.
- Give every numerical criterion score a same-line filing or calculation citation for the evidence used to assign that score.
- End each analyst output with one final nonblank line that begins exactly `Insight:`.
- The Insight must use exact supplied citation tokens and must not merely restate the earnings release's first paragraph.
- Do not write a four-digit year in an Insight unless the year has its own exact source citation.
