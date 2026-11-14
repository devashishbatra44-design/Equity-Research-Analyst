# Week 4 Requirement Trace

Checked: November 14, 2026

## Lab 06: seeker

| ID | Requirement | Planned evidence | State |
|---|---|---|---|
| S01 | Accept a distribution start date. | Skill contract and date-range functions | Implemented; live run pending |
| S02 | Read Form 10, amendments, CERT, filing folders, and parent distribution 8-Ks. | Synthetic SEC index and filing-folder tests | Implemented; real filing validation pending |
| S03 | Send a declared SEC User-Agent and remain below 10 requests per second. | Request client test | Verified |
| S04 | Save parent, ratio, record date, distribution date, filing, and section. | Registry schema and fixture | Verified |
| S05 | Leave a missing fact blank and say it is missing. Never estimate it. | Missing-field test | Verified |
| S06 | Drop a non-spin with a reason and filing. | Synthetic non-spin fixture | Verified |
| S07 | Assign registered, listing approved, trading, in window, or past stage. | Stage truth table | Verified |
| S08 | Use the parent CIK to find the distribution 8-K. | Parent-CIK submissions fixture | Verified |
| S09 | Use the first regular close after distribution. Never use when-issued trading. | Price-date test | Verified |
| S10 | Read human factors with direction, weight, and window. | `HUMAN_FACTORS.md` plus parser | Waiting for human input |
| S11 | Print points by factor. | Rank calculation test | Verified |
| S12 | Leave a name unranked when a required date is missing. | Missing-date test | Verified |
| S13 | First line states run date, price date, and index date. | Report snapshot test | Verified |
| S14 | Report ranked, watch, dropped, and data-limit sections. | Report fixture | Verified |
| S15 | End with `screens, not recommendations` exactly. | Exact-line test | Verified |
| S16 | Save a dated run. | Filesystem test | Pending |
| S17 | Test every rule with synthetic data before a real company run. | Offline suite | Verified for implemented rules |
| S18 | Code and skill names contain no company name. | Path/name review | Verified |

## Lab 07: worksheet

| ID | Requirement | Planned evidence | State |
|---|---|---|---|
| W01 | Run on a saved team seeker result and saved filings. | CLI contract test | Pending |
| W02 | Save Form 10 and the information statement by accession when the name is in the registry. | Filing fixture test | Pending |
| W03 | Use `not applicable` for spin sections when the name is outside the registry. | Branch test | Pending |
| W04 | Emit one line per fact with an amount or `not known`. | Renderer test | Verified |
| W05 | Separate historical, pro forma, and post-spin facts. | Schema test | Verified |
| W06 | Record parent, ratio, dates, debt/cash destination, liabilities, restrictions, Form 4 code P, and liquidity. | Fact checklist test | Pending |
| W07 | Compare median daily dollar volume with the client purchase size. | Code calculation test | Code verified; waiting for human client size |
| W08 | Print owner cash flow as after-tax earnings + depreciation - capex. | Arithmetic test | Verified |
| W09 | Compute low and mid values from human rates and compare price with the low value. | Truth table | Code verified; waiting for human config |
| W10 | Make one model call with the human persona only for why cheap, why not cheap, and the next filing that changes the view. | Stub-model prompt test | Waiting for human persona |
| W11 | Add liquidity by code after the model call. | Ordering test | Pending |
| W12 | End with a release view, one deciding number and citation, conviction under the human rule, and a not-known list. | Output contract test | Waiting for human rules |
| W13 | Use `not computed` when no close is available. | Missing-price test | Verified |
| W14 | Save a dated result. | Filesystem test | Pending |
| W15 | Do not let a model compute a number. | Prompt and output verifier tests | Pending |

## Numeric hook

| ID | Requirement | Planned evidence | State |
|---|---|---|---|
| H01 | Read every number from the saved worksheet. | Scanner coverage test | Verified |
| H02 | Verify exact tag, period, filing, and saved text line. | Saved-line fixture | Verified |
| H03 | Recompute printed arithmetic from printed inputs. | Seeded arithmetic tests | Verified |
| H04 | Verify rates and weights against human config. | Config mismatch tests | Verified |
| H05 | Verify price through the closes reader. | Saved reader-record test | Verified |
| H06 | Ignore only dates, accessions, and line numbers as numeric categories. | Scanner truth table | Verified |
| H07 | Fail an unknown numeric kind. | Unknown-number test | Verified |
| H08 | Print the refusal line when blocked. Stay silent when clean. | Seeded-error and clean tests | Verified |
| H09 | Show the hook file before enabling it. | Human review receipt | Waiting for review |
| H10 | With the Stop hook enabled, a seeded output cannot finish. | Controlled hook test | Waiting for review |

## Live record and hit rate

| ID | Requirement | Planned evidence | State |
|---|---|---|---|
| L01 | Select at least one release or SEC report filed in each selected live week. | Team decision record | Pending |
| L02 | Commit and push the report within 24 hours of EDGAR Accepted time. | Accepted time, permanent commit link, and Git commit timestamp | Pending |
| L03 | A report begins with the filings used. Include the release when the event is an earnings release. | Report contract test | Pending |
| L04 | Save Week 4 live work under `week04/runs/live/` and record the pushed commit in `LIVE_RECORD.md`. | Dated folder and live-record row | Pending |
| L05 | Record ticker, filing time, view time, direction, reaction, agree/disagree, and after flag. | Hit-rate schema | Verified |
| L06 | Measure reaction from last close before filing to first close after filing. | Price test | Verified |
| L07 | Exclude `after` and `not computed` rows from the scored count. | Summary test | Verified |
| L08 | Do not upload a separate weekly report to Brightspace. Starting with Checkpoint 3, list the live record completed so far. | Checkpoint submission record | Pending |

## Human-only controls

The following decisions must remain human-authored:

- the two chapter notes;
- the two hand-found Form 10 examples;
- factors, directions, weights, and window;
- worksheet low and mid rates;
- the investor persona and conviction rule;
- client purchase size;
- live filing and runner;
- owned product line.

Codex can check completeness and syntax after Devashish writes these items. Codex must not invent them.
