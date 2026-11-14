---
name: fin67110-investor-worksheet
description: Build or audit the FIN 67110 Week 4 investor worksheet, numeric verifier, hit-rate row, and live report from a saved seeker result. Use for Lab 07 work after the human configuration and persona are frozen.
---

# FIN 67110 Investor Worksheet

Use a saved seeker result and saved filings. Do not run this skill until the human worksheet configuration and persona are frozen.

## Fact worksheet

Save the Form 10 and information statement by accession when the name is in the registry. Mark spin sections `not applicable` when the name is outside the registry.

Write one line per fact. Each line contains an amount or `not known`, units, period, form, accession, URL, and filing section. Separate historical, pro forma, post-spin, and transaction facts.

Cover parent, ratio, dates, debt and cash destination, liabilities, restrictions, Form 4 code `P` purchases, and liquidity. Compute median daily dollar volume and compare it with the frozen client purchase size.

Use `equity_research_crewai.investor_worksheet` for owner cash flow, the low and mid values, liquidity, and rendering. The owner cash flow formula is after-tax earnings plus depreciation minus capital expenditures.

## Model boundary

Make one model call. Give it only the human-written persona and saved, cited facts or code calculations. Ask only why the security may be cheap, why it may not be cheap, and which next filing fact would change the view. The model must not compute a number.

Add liquidity in code after the model call. End with the release view, one deciding number and citation, conviction under the frozen rule, and the `not known` list. Use `not computed` when no close is available.

## Verification and live record

Use `equity_research_crewai.numeric_hook` to check every numeric claim in the saved structured worksheet. Seed one arithmetic error by 1 and confirm refusal. Confirm a clean file produces no output. Show the hook file to the student before enabling any Stop hook.

Use `equity_research_crewai.hit_rate` for the reaction row. Exclude `after` and `not computed` rows from the scored count.

Begin the live report with the filings used. Save it under `week04/runs/live/`. The team must push its commit within 24 hours of EDGAR Accepted time.
