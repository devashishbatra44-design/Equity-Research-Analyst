# Equity Research Desk App

Add the four roles from Figure 1 of Francis and Zhang (2026) to the existing seven-step SEC data pipeline.

Use the official Python SDK for the configured model provider.

Read the model key from `API_KEY` in `.env`. You may also accept `GENAI_API_KEY` as the local Purdue GenAI Studio key name.

Never print, log, save, or commit the key.

Do not hard-code a company name, ticker, CIK, filing, peer, date, price, fiscal year, or financial value in the desk code.

## Command-line interface

1. Accept one required ticker.
2. Accept a required comma-separated `--peers` list.
3. Accept a required numeric `--price`.
4. Accept a required `--price-date` in `YYYY-MM-DD` format.
5. Accept a required `--price-source`.
6. Permit a successful saved data run to be reused.
7. Validate that the saved run belongs to the requested ticker.
8. Validate that the saved price, price date, and price source match the command.

## JSON hand-off

Give each role one JSON message.

The JSON message must contain these fields:

- `task`
- `context`
- `expected_output`

Give each role only the context that the Strategy Manager assigns to it.

Make each role a separate model call.

Print the role name when each model call starts.

Write 80% of the way to ASD-STE100.

Use short sentences.

Use active voice.

Keep every number, condition, and hedge.

Never invent a fact, number, source, quotation, filing line, or calculation.

## Research Analyst

1. Use only the 10-K Business section, the 10-K MD&A section, and the earnings release in the assigned JSON context.
2. Describe the business model.
3. Describe the competitive position.
4. Describe catalysts.
5. Describe recent developments.
6. Support every factual claim with a short exact quotation.
7. State the source filename and line number for every quotation.
8. State that the filing does not establish a claim when the supplied sources do not support it.
9. Return only these exact Markdown sections:
   - `## Overview`
   - `## Market Positioning and Growth Outlook`
   - `## Future Developments and Strategic Recommendations`

## Financial Analyst

1. Use only the Step 4 facts, Step 5 calculations, Step 6 quarterly release claims, Step 7 peer facts, and supplied source-line excerpts.
2. Never calculate in the model.
3. Ask the code calculator for every additional ratio.
4. State all 11 required audit claims.
5. State annual total revenue.
6. State annual revenue growth.
7. State operating income and operating margin.
8. Use total revenue as the operating-margin denominator.
9. State net income attributable to the company.
10. State annual GAAP diluted EPS.
11. State return on average equity.
12. State debt to equity with the current portion of long-term debt included.
13. State free cash flow as cash from operations minus additions to property and equipment.
14. State quarter revenue.
15. State quarter revenue growth versus the same quarter last year.
16. State quarter GAAP diluted EPS.
17. Use the earnings-release quarter-end date.
18. Do not substitute the latest 10-Q date for the release quarter-end date.
19. State P/E as the supplied price divided by the latest fiscal-year diluted EPS.
20. State the price date and price source.
21. Label this measure `FY-EPS P/E`.
22. Never label it `TTM P/E`.
23. State every supplied peer operating margin.
24. Name the revenue definition when a filing offers more than one definition.
25. Give every number its filing and accession number.
26. Give every number its period and unit.
27. Give every number its XBRL tag or exact filing line.
28. Show the code-supplied arithmetic for every ratio.
29. State `unavailable` when a required source value is unavailable.
30. Never estimate a missing filing value.
31. Return only `## Valuation Insights`.

## Investment Advisor

1. Use only the Research Analyst output and the Financial Analyst output.
2. Write a thesis.
3. State one recommendation: Buy, Hold, or Sell.
4. Name one reported number that decides the recommendation.
5. State the number's period.
6. Do not add a company fact, number, or reason from memory.
7. Prefer Hold when the supplied analysis cannot establish value.
8. Explain that one multiple without a suitable comparison does not establish intrinsic value.
9. State that the recommendation is not financial advice.
10. Return only `## Investment Recommendation`.

## Strategy Manager

1. Check for these five exact report parts:
   - `Overview`
   - `Market Positioning and Growth Outlook`
   - `Valuation Insights`
   - `Future Developments and Strategic Recommendations`
   - `Investment Recommendation`
2. Check that the sections are consistent with the role outputs.
3. Check that each numerical claim is supported by a supplied role output.
4. Check that the recommendation names a number in the report.
5. Return a structured status of `pass` or `retry`.
6. Name every section that requires a retry.
7. Send a failing section back to its responsible role once.
8. Never send a section back more than once.
9. Recheck the report after the one permitted retry.
10. Stop without marking the report complete if a required section or issue remains unresolved.

## Saved report

1. Save the report as `report.md` in the run folder.
2. Put the filings read and their accession numbers on line 1.
3. Put the run time on line 2.
4. Compile the five required sections in the required order.
5. Print the report path.
6. Save the three analyst role outputs.
7. Save the Strategy Manager review.
8. Create a separate manual-audit worksheet.
9. Leave every student audit mark blank in a newly generated worksheet.
10. Never let the model choose a student audit mark.
11. End every public report and audit with these three lines:

```text
This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex built the desk; Purdue GenAI Studio generated the draft. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
```

## Completion check

Run the app on a ticker with at least three peers and a supplied price.

Confirm these conditions:

1. Steps 1 through 7 finish successfully.
2. The Research Analyst runs.
3. The Financial Analyst runs.
4. The Investment Advisor runs.
5. The Strategy Manager runs.
6. The report contains the five required sections.
7. The report contains the filing-accession line.
8. The report contains the run-time line.
9. The report path prints.
10. The manual-audit worksheet exists.
11. `.env` remains outside Git.

Complete the implementation.

Do not stop after writing a plan.
