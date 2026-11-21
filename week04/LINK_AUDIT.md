# Week 4 Link Audit

Checked: November 21, 2026

Entry point: <https://cinderzhang.github.io/FIN67110-Fall2026/schedule.html>

## Scope rule

This audit covers all links on the Week 4 overview, Lab 06, Lab 07, and the Week 4 request page. It also covers each named Week 4 target on the course readings, data, project, and deck pages.

An external target page is a boundary. Unrelated navigation on SEC, LSEG, Purdue, YouTube, GitHub, publisher, and documentation sites is outside the course link graph.

## Fresh recheck on November 21, 2026

- The Schedule, Week 4 overview, Lab 06, Lab 07, request samples, Project, Grading, Syllabus, decks, readings, data, Week 3, Week 5, and audit-checklist pages returned HTTP 200.
- The primary Week 4 content and requirements did not change from the saved November 20 copies.
- The Claude, Codex, Antigravity, YouTube, GitHub, DOI, LSEG, WRDS, CRSP, and other method targets were reached, subject to normal publisher or institutional access controls.
- Automated requests to SEC pages returned HTTP 403 without the required SEC request identity. The saved course work uses a declared SEC User-Agent and already contains the primary filing evidence.
- The Purdue Capital IQ page and the Purdue-hosted McConnell PDF had a local certificate-chain verification error during this automated recheck. This does not prove that either page is unavailable in a browser.
- The Week 4 course site contains four broken fragment links on `requests.html`. The page uses double-hyphen IDs, but its links use single-hyphen fragments. The underlying request page returned HTTP 200 and was reviewed in full.

## Primary pages

| Page | Status | Governs |
|---|---|---|
| [Schedule](https://cinderzhang.github.io/FIN67110-Fall2026/schedule.html) | Reviewed | Week 4 dates and live-record window |
| [Week 4 overview](https://cinderzhang.github.io/FIN67110-Fall2026/week-04/index.html) | Reviewed in full | Mission, outcomes, readings, prework, live record, and ship target |
| [Lab 06: The seeker](https://cinderzhang.github.io/FIN67110-Fall2026/week-04/lab-06-investor-skill.html) | Reviewed in full | Spinoff registry, pricing, factors, ranking, tests, and known answers |
| [Lab 07: Your investor](https://cinderzhang.github.io/FIN67110-Fall2026/week-04/lab-07-your-investor.html) | Reviewed in full | Worksheet, persona call, numeric hook, hit-rate table, and live report |
| [Week 4 request samples](https://cinderzhang.github.io/FIN67110-Fall2026/week-04/requests.html) | Reviewed in full | ASD-STE100 samples for the seeker, worksheet, hook, and closes reader |

## Course sublinks reached from Week 4

| Link | Status | Week 4 use |
|---|---|---|
| [Margin of safety deck](https://cinderzhang.github.io/FIN67110-Fall2026/decks/margin-of-safety.html) | Reviewed in full | Low-end value, range not point estimate, catalysts, and code/model/hook split |
| [Readings](https://cinderzhang.github.io/FIN67110-Fall2026/reference/readings.html) | Week 4 section reviewed | Required and optional evidence map |
| [Data](https://cinderzhang.github.io/FIN67110-Fall2026/reference/data.html) | Reviewed in full | SEC, LSEG, WRDS, licensing, and reader interface |
| [Project live record](https://cinderzhang.github.io/FIN67110-Fall2026/project.html#the-live-record) | Reviewed in full, then clarified by the instructor message | 24-hour GitHub push rule and Weeks 4-7 gate |
| [Week 3 persona anchor](https://cinderzhang.github.io/FIN67110-Fall2026/week-03/index.html#teaching-3--the-persona-dynamic-work-in-a-fixed-slot) | Reviewed | Human persona stays in a fixed model slot |
| [Week 5 preview](https://cinderzhang.github.io/FIN67110-Fall2026/week-05/index.html) | Reviewed for dependency | Lab 07 hands its record to Week 5 |
| [Grading](https://cinderzhang.github.io/FIN67110-Fall2026/grading.html) | Reviewed for live-record and project gates | Grade rules and absence/outage rules |
| [Syllabus](https://cinderzhang.github.io/FIN67110-Fall2026/syllabus.html) | Reviewed for hierarchy | Public course rules; Brightspace holds official Purdue text |
| [Deck index](https://cinderzhang.github.io/FIN67110-Fall2026/decks/index.html) | Reviewed | The lab page governs when a deck differs |

Global navigation links to Home, Schedule, Grading, Project, Syllabus, and Decks occur on each course page. They were deduplicated after review.

## Required reading targets

| Target | Status | Required action |
|---|---|---|
| Joel Greenblatt, *You Can Be a Stock Market Genius* (1997), Chapter 3 | Book; no public course URL | Human reads about 40 minutes and writes who sells and why the sale is unrelated to value |
| Seth Klarman, *Margin of Safety* (1991), Chapter 10 spinoff pages | Book; no public course URL | Human reads about 20 minutes and writes when the parent is cheap; Greenblatt carries the week if unavailable |
| [Claude skills](https://code.claude.com/docs/en/skills) | Reviewed | Skill folder and `SKILL.md` model |
| [Claude hooks](https://code.claude.com/docs/en/hooks) | Reviewed | Deterministic hook events and review risk |
| [Claude hook guide](https://code.claude.com/docs/en/hooks-guide) | Reviewed | Hook setup examples |
| [Codex skills](https://learn.chatgpt.com/docs/build-skills) | Reviewed | Repository skills live under `.agents/skills` |
| [Codex hooks](https://learn.chatgpt.com/docs/hooks) | Reviewed | Repository hook config and Stop blocking behavior |
| [Antigravity skills](https://antigravity.google/docs/skills) | Reviewed | Workspace skills under `.agents/skills` |
| [Antigravity hooks](https://antigravity.google/docs/hooks) | Reviewed | Stop hook can return a continue decision |
| [Hooks video](https://youtu.be/03CfGf9iw_U) | Target reached | Optional support for the hook reading |
| [Codex hooks video](https://www.youtube.com/watch?v=mT1z7wQoxzs) | Target reached | Optional support for the hook reading |

## Optional repositories and method references

| Target | Status | Course-safe conclusion |
|---|---|---|
| [FAskills](https://github.com/CinderZhang/FAskills) | README and processing architecture reviewed | Reuse the raw-data-to-deterministic-metrics pattern; preserve SEC provenance and course personas |
| [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | README reviewed; not installed | It uses paid Financial Datasets data and investor agents; do not copy its recommendation or voting design |

## Spinoff evidence and filing references

| Target | Status | Use |
|---|---|---|
| [Cusatis, Miles, and Woolridge](https://doi.org/10.1016/0304-405X(93)90009-Z) | Metadata target reached | Historical 1965-1988 spinoff evidence |
| [Desai and Jain](https://doi.org/10.1016/S0304-405X(99)00032-X) | Metadata target reached | Historical 1975-1991 spinoff evidence |
| [McConnell et al. PDF](https://business.purdue.edu/faculty/mcconnell/publications/spinoffs-ex-ante-2001-vol74.pdf) | Target reached | 1989-1995 evidence; matched and factor benchmarks matter |
| [Review abstract](https://english.phbs.pku.edu.cn/2015/Publications_1001/243.html) | Target reached | Later literature context |
| [Review DOI](https://doi.org/10.1111/j.1468-2370.2008.00243.x) | Metadata target reached | Review evidence |
| [Recent underperformance note](https://boyarresearch.substack.com/p/spinoffs-have-dramatically-underperformed) | Target reached; optional commentary | Current claims need a pre-registered check before use |
| [S&P index launch](https://press.spglobal.com/2015-08-04-S-P-Dow-Jones-Indices-Launches-Spin-Off-IPO-and-Activist-Interest-Indices) | Target reached | Index history is not proof of historical membership |
| [SEC Form 10](https://www.sec.gov/files/form10.pdf) | Reviewed | Registration statement under Exchange Act Section 12(b) or 12(g) |
| [EDGAR form types](https://www.sec.gov/info/edgar/forms/edgform.pdf) | Target reached | Form-code definitions |
| [Staff Legal Bulletin No. 4](https://www.sec.gov/interps/legal/slbcf4.txt) | Target reached | Spinoff registration context |
| [SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf) | Reviewed | Parent announcement and distribution evidence |
| [SEC Form 4](https://www.sec.gov/files/form4.pdf) | Reviewed | Insider purchase code and transaction evidence |
| [EDGAR full-text search](https://www.sec.gov/edgar/search/) | Reviewed | Search Form 10 information statements |
| [EDGAR full-text FAQ](https://www.sec.gov/edgar/search/efts-faq.html) | Reviewed | Search coverage and query behavior |
| [Accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) | Reviewed | Declared User-Agent and maximum 10 requests per second |
| [Preset information-statement search](https://www.sec.gov/edgar/search/#/q=%22information%20statement%22&forms=10-12B) | Target reached | Human finds one genuine spinoff and one non-spinoff Form 10 |

## Data targets

| Target | Status | Week 4 rule |
|---|---|---|
| [SEC ticker-to-CIK JSON](https://www.sec.gov/files/company_tickers.json) | Reviewed | Public identifier map |
| [SEC submissions example](https://data.sec.gov/submissions/CIK0000909832.json) | Reviewed | Filing metadata and Accepted time path |
| [SEC company facts example](https://data.sec.gov/api/xbrl/companyfacts/CIK0000909832.json) | Reviewed | Tagged facts with period, unit, and accession controls |
| [Purdue LSEG guide](https://guides.lib.purdue.edu/refinitivworkspace) | Target reached; Purdue access may expose more | Workspace registration and access |
| [LSEG Data Library](https://pypi.org/project/lseg-data/) | Reviewed | Optional local package; current audited PyPI release was 2.1.1 |
| [LSEG Python quick start](https://developers.lseg.com/en/api-catalog/lseg-data-platform/lseg-data-library-for-python/quick-start/getting-started-with-python) | Reviewed | Desktop session needs Workspace running and an App Key |
| [Purdue WRDS guide](https://guides.lib.purdue.edu/WRDS) | Target reached; Purdue access may expose more | Historical backtest access |
| [WRDS Python package](https://pypi.org/project/wrds/) | Target reached | Licensed historical data stays out of model prompts |
| [Purdue Capital IQ note](https://blogs.lib.purdue.edu/news/2024/04/08/featured-databases-sp-capital-iq/) | Target reached | Optional export source; raw exports stay local |
| [CRSP data descriptions](https://clouddc.chass.utoronto.ca/ds/crsp/en/manuals/data_descriptions_guide.pdf) | Target reached | Historical price and identifier definitions |
| [Historical S&P membership note](https://library.smu.edu.sg/topics-insights/notes-and-thoughts-retrieving-historical-members-sp-500-wrds) | Target reached | Current membership must not stand in for historical membership |

## Project targets

| Target | Status | Week 4 use |
|---|---|---|
| [Report audit](https://cinderzhang.github.io/FIN67110-Fall2026/reference/audit-checklist.html) | Reviewed | Financial claim marks and definitions |
| [Nasdaq earnings calendar](https://www.nasdaq.com/market-activity/earnings) | Target reached | Candidate discovery only |
| [EDGAR company search](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany) | Reviewed | Filing and Accepted-time source |

## Findings that change the work

1. The old local audit used retired Lab 06 and Lab 07 URLs. The current pages are `lab-06-investor-skill.html` and `lab-07-your-investor.html`.
2. Week 4 is published. It is not a placeholder.
3. Week 4 requires Greenblatt Chapter 3, Klarman Chapter 10 spinoff pages when available, and the skill/hook documentation. Graham, Buffett, and Marks are not the current required Week 4 list.
4. The first live-record window is November 9-15, 2026.
5. The public project page says 3 students per team. Devashish confirms that Professor Zhang permitted the current 4-person team. The exception is user-confirmed because the original message is not stored in the repository.
6. The installed environment has CrewAI 1.9.3. The downloaded local CrewAI skill notes target 1.15.x. Do not copy 1.15.x-only API forms into this project without checking the installed source.
7. `lseg-data` is not installed in the repository virtual environment. The closes reader therefore supports a licensed local export and reports `not available` until the package or an export is present.
8. Professor Zhang clarified that each weekly report is committed and pushed to the team GitHub repository within 24 hours. There is no separate weekly Brightspace upload. The pushed commit timestamp is the record.
9. Starting with Checkpoint 3, the checkpoint upload lists the live record completed so far.
10. The grading weights are four checkpoints at 17.5% each, the project at 20%, and peer evaluation at 10%.
11. The project tiers are 95, 85, 70, and 0. The fail gate applies when the repository has no live report or the team has no product manual.
12. The seeker report must end with `screens, not recommendations` exactly.

## Recheck rule

Recheck the Schedule, Week 4 overview, Lab 06, Lab 07, Project, Data, and Readings pages before any submission or live report. Record a changed requirement in this file before changing code.
