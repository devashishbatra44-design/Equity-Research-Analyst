---
name: fin67110-spinoff-seeker
description: Build or audit the FIN 67110 Week 4 spinoff registry and seeker screen from SEC filings, frozen human factors, and official regular closes. Use for Lab 06 seeker work. Do not use it to make an investment recommendation.
---

# FIN 67110 Spinoff Seeker

Create a dated, reproducible screen. Treat it as a screen and not a recommendation.

## Inputs

Require a distribution start date and the frozen `week04/HUMAN_FACTORS.md` file.

Use SEC form indexes, filing folders, Form 10 amendments, certification filings, and the parent CIK's distribution 8-K. Send a declared SEC User-Agent on every request. Stay below 10 requests per second.

Use `equity_research_crewai.spinoff_seeker` for deterministic staging, scoring, first-close selection, and rendering. Do not add a company name to reusable code.

## Registry rules

Save the child, parent, both CIKs, distribution ratio, record date, distribution date, filing accession, URL, and section. Leave a missing fact blank. State that it is missing. Never estimate it.

Drop non-spinoffs. Save the reason and the filing section that proves the reason.

Use only the first regular close after distribution. Do not use when-issued trading.

## Ranking rules

Use only the human-frozen factors, directions, weights, windows, and missing-data rules. Print each factor's points. A missing required date makes the name unranked.

Test every rule with synthetic data before a live company run. Include a zero-weight test.

## Output contract

The first line states run date, price date, and index date. Include `Ranked`, `Watch`, `Dropped`, and `Data limits` sections. Save a dated run.

The exact last line is:

`screens, not recommendations`
