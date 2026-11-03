# FIN 67110 Course Playbook

Last audited: October 27, 2026  
Time zone for deadlines: Eastern Time  
Student: Devashish Batra  

This is a living control document for FIN 67110, Fall 2026. It records published course requirements, current evidence, open risks, and the checks to run before each submission. The official course site and Brightspace remain authoritative.

## Source hierarchy

Use these sources in this order when requirements differ:

1. The current lab page governs the work performed in that lab.
2. The [schedule](https://cinderzhang.github.io/FIN67110-Fall2026/schedule.html) governs dates.
3. The [grading page](https://cinderzhang.github.io/FIN67110-Fall2026/grading.html) governs points and policies.
4. The [project page](https://cinderzhang.github.io/FIN67110-Fall2026/project.html) governs the five project parts, the live record, and project ranking.
5. The [data page](https://cinderzhang.github.io/FIN67110-Fall2026/reference/data.html) governs the data reader and licensed-data handling.
6. The [report audit](https://cinderzhang.github.io/FIN67110-Fall2026/reference/audit-checklist.html) governs financial claim definitions and audit marks.
7. Brightspace holds submissions, timestamps, the official Purdue syllabus, the team list, and the presentation order.

The public syllabus page says that the course pages govern. The session decks also say that the lab page governs.

## Grade control

| Component | Weight | Complete requirement |
|---|---:|---|
| Checkpoint 1 | 17.5% | By 11:59 PM Eastern on Session 3: submit a permanent commit link to the desk and a report on the partner's company. A fallback report counts. |
| Checkpoint 2 | 17.5% | By 11:59 PM Eastern on Session 5: submit a permanent commit link to the verifier and its marks on the seeded-error test. |
| Checkpoint 3 | 17.5% | By 11:59 PM Eastern on Session 9: submit one team Markdown page naming the team, client, client-layer design, and live record so far. |
| Checkpoint 4 | 17.5% | By 11:59 PM Eastern on Session 12: submit the team draft paper with the live-record table, audit table, and client paragraph. |
| Project | 30% | Submit all five project parts. The project is ranked once. |

Each checkpoint is 100 or 0. There is no partial credit. Checkpoints 1 and 2 are individual. Checkpoints 3 and 4 are team submissions.

The project scores are 95 for the top tier, 85 for the standard tier, and 0 for a failed project. A course grade of A starts at 93. With all four checkpoints complete, the published totals are 98.5 for a top-tier project and 95.5 for a standard-tier project. Each missed checkpoint costs 17.5 course points.

The fail rule is checked first. The project fails if no live-record note ever reaches Brightspace or if the team submits no paper.

## Calendar and hard deadlines

| Session | Date | Work | Due by 11:59 PM Eastern |
|---:|---|---|---|
| 1 | Thu Oct 22 | Lab 01: Ready to Build | Session 1 checkout moved to Mon Oct 26 |
| 2 | Tue Oct 27 | Lab 02: The Desk's Steps | No checkpoint |
| 3 | Thu Oct 29 | Lab 03: The App | Checkpoint 1 |
| 4 | Tue Nov 3 | Lab 04: The Verifier | No checkpoint |
| 5 | Thu Nov 5 | Lab 05: The Desk's Hands | Checkpoint 2; teams formed |
| 6 | Tue Nov 10 | Lab 06: The Investor's Desk | No checkpoint |
| 7 | Thu Nov 12 | Lab 07: Your Investor View | No checkpoint |
| 8 | Tue Nov 17 | Lab 08: The Institution's Desk | No checkpoint |
| 9 | Thu Nov 19 | Lab 09: Your Portfolio Under a Mandate | Checkpoint 3 |
| 10 | Tue Nov 24 | Lab 10: Break Your Desk | No checkpoint |
| — | Thu Nov 26 | Thanksgiving; no class | — |
| 11 | Tue Dec 1 | Lab 11: Write for Your Client | No checkpoint |
| 12 | Thu Dec 3 | Lab 12: Consulting | Checkpoint 4 |
| 13 | Tue Dec 8 | Presentations | Presentation group assigned in Brightspace |
| 14 | Thu Dec 10 | Presentations | Presentation group assigned in Brightspace |
| — | Fri Dec 11 | Final project | Project due at 11:59 PM Eastern |

Live-record windows run Monday through Sunday:

- Week 4: November 9–15.
- Week 5: November 16–22.
- Week 6: November 23–29. A report is welcome, but this is the intended optional week.
- Week 7: November 30–December 6.

To remain eligible for the top project tier, the team needs an in-window report in at least three of the four weeks. Each report must use a release filed that week and reach Brightspace within 24 hours of the EDGAR Accepted time.

## The desk architecture

The desk follows Francis and Zhang (2026), Section 3.1.

| Role | Allowed inputs and tools | Required output |
|---|---|---|
| Strategy Manager | Role outputs, JSON task assignments, and a checklist | Assign tasks, check all five report parts, return an incomplete part once, and compile the report. |
| Research Analyst | Filing reader | Business model, competitive position, catalysts, and recent developments. Each claim needs a filing line. |
| Financial Analyst | Filing reader, XBRL facts, and code calculator | Financial statements, growth, margins, returns, leverage, cash flow, peers, sources, definitions, and arithmetic. |
| Investment Advisor | Research and Financial Analyst outputs only | Thesis, Buy/Hold/Sell, and the one deciding number. |

The five report parts are:

1. Overview.
2. Market Positioning and Growth Outlook.
3. Valuation Insights.
4. Future Developments and Strategic Recommendations.
5. Investment Recommendation.

Each role is a separate model call. The manager's fixed loop, prompts, tools, saved task state, and checks form the harness. Figure 1 is therefore best described as a workflow made of agent-like model calls because code fixes the main path.

## The seven data steps for Lab 02

The [Lab 02 page](https://cinderzhang.github.io/FIN67110-Fall2026/week-02/lab-02-desk-on-one-page.html) contains the exact request that must be sent to the coding agent. The finished program must accept a ticker, optional peers, an optional price, and an optional single-step selector. No company name may be hard-coded.

1. Resolve the ticker to the SEC CIK.
2. Select the latest 10-K, latest 10-Q, and latest 8-K that reports Item 2.02. Record accession numbers and EDGAR Accepted times.
3. Download the filings and the 8-K's Exhibit 99.1. Convert them to text and save a timestamped run folder.
4. Read the latest fiscal year's XBRL facts. Choose the candidate tag whose latest year is newest. Keep all concepts on the same fiscal-year end as revenue.
5. Compute every ratio in code and show the arithmetic.
6. Extract the release lines for quarterly total revenue and GAAP diluted EPS.
7. Run the same facts and operating-margin definition for each peer.

Lab 02 validation is manual. Match every number to the filing. Confirm each period end. Recompute every ratio. Confirm each peer comes from its own filing.

## The fixed report audit

The first 11 rows are mandatory for every report.

| # | Claim | Required definition or source |
|---:|---|---|
| 1 | Latest fiscal-year total revenue | 10-K income statement and revenue tag for that period |
| 2 | Revenue growth | Current-year revenue divided by prior-year revenue, minus 1 |
| 3 | Operating income and operating margin | Operating income divided by total revenue |
| 4 | Net income attributable to the company | 10-K income statement |
| 5 | GAAP diluted EPS | 10-K per-share section |
| 6 | Return on average equity | Net income divided by the average of current- and prior-year equity |
| 7 | Debt to equity | Long-term debt, including the current portion, divided by equity |
| 8 | Free cash flow | Cash from operations minus additions to property and equipment |
| 9 | Latest-quarter revenue | Earnings-release income statement |
| 10 | Quarterly revenue growth | Current quarter divided by the same quarter last year, minus 1 |
| 11 | Latest-quarter GAAP diluted EPS | Earnings-release per-share section |

Then audit every other number in the Financial Analyst section, the five-part template, and the recommendation.

Use only these marks:

- **Correct:** the filing agrees after rounding, or the filing inputs and arithmetic support the computed value.
- **Wrong:** the report does not match the filing. Record the filing value.
- **Unsupported:** the report gives a number for a different period or definition, or a number the filing does not contain.
- **Missing:** the report omits a required claim. An adjusted EPS alone does not satisfy a GAAP EPS claim.
- **Not in filings:** the filing does not state the claim and the report gives no number. This does not count for or against a desk.

Report two counts at the top of each audit: errors, which equal wrong plus unsupported, and missing claims.

## Data contract

The desk must implement three functions for any ticker:

1. Return the five most recent fiscal quarters reported on or before a specified date and time. Return period end, revenue, net income, total debt, and cash, in millions.
2. Return official daily closes between two dates.
3. Return the last official close before a specified date and time. Treat 4:00 PM Eastern as the close of a trading day.

Live data comes from LSEG. Backtest data comes from WRDS. The function interfaces must stay the same.

Before use, compare one returned close with the exchange and one returned quarter with the filing. Do not substitute adjusted close or a vendor-standardized accounting field for the course definition.

Licensed raw data must stay out of the repository. If provider terms prohibit model use, keep the values in code. Append the derived context table after the model roles finish. Do not show the raw licensed data to a model.

## Final project control

One Markdown file in Brightspace must contain permanent GitHub links for parts 1, 3, and 4 and identify the presentation session:

1. Desk tree at a fixed commit.
2. Live record already held in Brightspace.
3. `audits.md` at a fixed commit.
4. `paper.md` at a fixed commit.
5. Presentation session.

The repository README must state the exact command to run the desk on any ticker.

The audit file contains four tables: two own live reports first, then two reports received from another team in Session 10. Each table starts with its error and missing counts.

The paper is Markdown and has a 3,000-word maximum, excluding tables. It must include the question and client, a desk diagram, the full live-record table, all four audit results, the client outcome with limited conclusions, and a decision log that includes the Week 6 attack table.

The presentation lasts 11 minutes plus 3 minutes of questions. Every member must answer one question about a number shown. The team must run the desk live on the instructor's U.S. company from the past 30 days. One retry is allowed if the network fails.

## Project ranking controls

The ranking questions are applied in this order:

1. **Ran live:** at least three of four weekly reports were inside the 24-hour window.
2. **Audits hold:** one wrong mark in a table is a slip. Two or more wrong marks in one table fail this criterion.
3. **Desk is general:** the desk runs on the instructor's ticker and a spot-checked core claim quotes a real filing line.
4. **Honest reading:** the paper says no more than the evidence supports.
5. **Each member can explain:** every member answers the presentation question.

Investment performance is not a ranking criterion. Honest reporting of poor results can still rank in the top tier.

## Current evidence audit

Status meanings:

- **Verified:** checked directly on this laptop or on the official site.
- **User-confirmed:** Devashish reported completion, but the evidence is outside this repository.
- **Exception:** the published rule and the current instruction differ.
- **Pending:** a required output is not yet complete or cannot yet be verified.

| Requirement | Status on Oct 27 | Evidence or action |
|---|---|---|
| Python 3.11 or later | Verified | `python` and `python3` both report 3.12.10. |
| Codex CLI | Verified | `codex-cli 0.163.0-alpha.11.1`. |
| Antigravity CLI | Verified | `agy 1.4.7`. Antigravity is running. |
| Orca installed and running | Verified | Orca 1.4.240 is running. Its Codex process names `/Users/devashish/Desktop/The Boss DB` as the workspace. |
| Codex and Antigravity use this folder | Verified/user-confirmed | Orca exposes this exact folder. The Antigravity screenshot shows `The Boss DB`; its local hub includes this folder. |
| Persistent agent writing rule | Verified | Root `AGENTS.md` contains the required ASD-STE100 instruction. Antigravity CLI identified that file as its loaded project instruction and reproduced the required sentence. |
| Model-provider API key | Verified | The local `.env` contains a Purdue GenAI key. The safe check reports presence without printing it. A prior minimal call returned `READY`. |
| `.env` excluded from Git | Verified | `.gitignore` excludes `.env`. Git history contains no `.env` commit. Three environment tests pass. |
| GitHub CLI connected | Verified | `gh` can read `devashishbatra44-design/Equity-Research-Analyst`. |
| Repository public | Verified | The repository is public for instructor access. `.env` remains ignored and absent from Git history. |
| LSEG, WRDS, and Capital IQ accounts | User-confirmed | Devashish reports registration and successful login with the Purdue account. |
| Week 1 paper and assigned media | User-confirmed | Devashish reports completing the reading and video. The repository records the required conclusions and definitions. |
| Costco filing exercise | Verified | The repository records the SEC filing links, periods, units, and revenue values. |
| Lab 01 partner demonstration | User-confirmed | Partner: Shivani Rathi. Devashish reports that the witnessed checks passed. |
| Session 1 Brightspace checkout | User-confirmed complete | Devashish confirms that Brightspace received the repository link and partner name, Shivani Rathi. |
| Lab 02 seven-step desk | Verified | The seven-step desk and saved runs are present and tested. |
| Lab 03 app and Checkpoint 1 | Verified/user-confirmed | The four-role app and audited reports are present. Devashish reports that Brightspace received the submission; the receipt remains outside this repository. |

Week 1 is complete. The public-repository requirement is satisfied.

## Immediate critical path

Today, October 27:

1. Week 2 source notes are recorded in `week02/README.md`; two student explanation checks remain.
2. Build the seven Lab 02 steps from the exact lab request.
3. Run the desk data path on Costco.
4. Validate every step against the instructor run and the filings.
5. Save facts and filing text without committing secrets or licensed raw data.

Before Session 3:

1. Finish any failed Costco step.
2. Run the unchanged steps on WMT with chosen peers.
3. Confirm WMT revenue, operating income, fiscal period, revenue definition, and operating margin against the latest 10-K.
4. Push the code and permitted saved facts. Never push `.env` or licensed exports.
5. Confirm the API-key presence check.

During Session 3:

1. Add the four separate model roles.
2. Produce the five-part Costco report.
3. Audit all 11 core claims by hand, then all other Financial Analyst numbers, the template, and recommendation.
4. Run the unchanged desk on the partner's U.S. company that reported that month.
5. Have the partner mark two core claims at the top of that report.
6. Commit and push the complete evidence.
7. Submit a permanent commit link to Brightspace Checkpoint 1 before 11:59 PM Eastern.

## Submission gate for every checkpoint

Do not submit until all applicable boxes pass:

- [ ] The output exactly matches the lab's checkout requirement.
- [ ] Every financial number has a source, period, units, filing, and definition.
- [ ] Code computes ratios. The model does not perform arithmetic.
- [ ] A human checked the required audit marks against the primary filings.
- [ ] The report names every filing it read.
- [ ] The code runs from the README command on a clean checkout.
- [ ] No company name is hard-coded in general desk code.
- [ ] `.env`, keys, raw licensed pulls, and vendor exports are absent from Git.
- [ ] Public material ends with the course's required three-line disclosure.
- [ ] The commit is pushed and the permanent link opens at that commit.
- [ ] The Brightspace submission is final, not a draft, and the confirmation receipt is saved.

## Public disclosure template

Anything made public must end with these exact three lines. Replace the bracketed text. The student must personally verify the sources before using the statement.

> This is a learning exercise, not financial advice.
>
> AI assistance: [the tools you used]. I verified the sources myself; the judgments are mine.
>
> Any remaining errors are my own.

## Fallback and outage rules

If the desk or model provider fails before Checkpoint 1 or a live record, use the [Week 2 fallback](https://cinderzhang.github.io/FIN67110-Fall2026/week-02/index.html#the-fallback). Paste the latest 10-K statements and earnings release into a model, send the four role tasks in one message, save a Markdown report whose first line names the company and filings, and put `fallback` on the second line. A fallback counts but is audited like any other report.

If Brightspace or GitHub is down at a checkpoint deadline, email the instructor before the deadline with everything the upload would contain. If Brightspace is down during a live-record window, email the report before the window closes. A personal setup failure is not an outage.

## Maintenance rule

Weeks 3–8 and Labs 04–14 were placeholders when checked on October 27. Recheck the relevant week and lab pages before starting each session. Update this file when a page is published. Never infer a missing requirement from the course sequence.

This playbook supports careful work. It cannot guarantee a grade. The grade depends on complete submissions, correct audits, live timing, team performance, and the instructor's published criteria.
