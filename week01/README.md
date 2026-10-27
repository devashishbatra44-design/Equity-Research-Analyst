# Week 1 — Ready to Build

## Lab 01 safety check

The local `.env` file stores credentials and the SEC User-Agent. It is ignored by Git. The `.env.example` file contains placeholders only.

Run the check from the project folder:

```sh
python3 week01/env_check.py
```

It reports only whether `GENAI_API_KEY` is present. It never prints the value. The tests use a fake value in a temporary file:

```sh
python3 -m unittest discover -s week01 -p 'test_*.py' -v
```

For the Lab 01 partner demonstration, run:

```sh
python3 check_env.py
```

No package installation is needed. The script reads `API_KEY` if present, or the existing `GENAI_API_KEY`, and prints the first four characters followed by `...`, then `SEC_USER_AGENT`, as the lab specifies. Run it only in the local terminal with your partner. Do not paste or screenshot the output. `.env` remains ignored by Git.

Enter your real key only in `.env`. Do not paste it into chat or screenshots. `api_smoke_test.py` sends one minimal prompt to the configured model and never prints the key.

`list_genai_models.py` makes an authenticated GET request and prints only the model IDs available to your account. The current local selection is `qwen3.8:27b`, which Purdue lists for coding and agentic workflows. `api_smoke_test.py` verifies one minimal chat-completions request.

## Concepts

- **Model:** a function that receives text and returns text. A call does not itself open files.
- **Harness:** the surrounding program. It controls the steps, tools, task state, and checks.
- **Agent:** a model plus a harness and a goal.
- **Workflow or agent?** Figure 1 is best described as a workflow implemented with agent-like model calls: the manager follows a fixed checklist and can return an incomplete section once. The models do not choose an unrestricted plan of their own.

In the desk, the model is each role's language-model call. The harness is the manager loop, prompts, filings reader, XBRL facts, calculator, and checks. The complete desk is the agent. The coding agent has a different harness: its tools are the project files and terminal.

## The four roles and their outputs

| Role | Inputs and tools | Responsibility |
|---|---|---|
| Strategy Manager | Role outputs; JSON task assignment and checklist | Assign work, check for all five report parts, return a missing part once, compile the report |
| Research Analyst | SEC filings reader | Business model, market position, catalysts, recent developments |
| Financial Analyst | SEC filings reader, XBRL facts, calculator | Statements, ratios, growth, peers, and source references |
| Investment Advisor | Research and financial outputs; no external tools | Thesis, Buy/Hold/Sell recommendation, and deciding number |

The five report parts are: **Overview; Market Positioning and Growth Outlook; Valuation Insights; Future Developments and Strategic Recommendations; Investment Recommendation.**

## Paper notes from the Week 1 course material

The course describes a four-agent system that wrote reports for 50 U.S. firms for 2024 Q3, compared with Value Line. The reported preferences were 71% for AI among four AI judges (with a wide 48%–96% judge range), 51% among MSF students, and 77% among the general public. Neither portfolio beat equal-weighted buy-and-hold. The key gap for this course: the study did **not** check whether the reports' financial numbers were correct.

## Costco filing exercise — checked against SEC EDGAR

As of October 26, 2026, the latest Costco earnings release with Item 2.02 is the September 24, 2026 8-K, Exhibit 99.1. The next later 8-K is not the earnings-results filing. The release reports results for the 16-week quarter and 52-week fiscal year ended August 30, 2026.

- **Quarter total revenue:** $95,723 million for the 16 weeks ended August 30, 2026. In Exhibit 99.1, use the consolidated statements of income, “Total revenue,” quarter column. This includes net sales plus membership fees; it is not the $93,873 million net-sales figure.
- **Prior-year quarter total revenue:** $86,156 million.
- **Calculated growth:** ($95,723m ÷ $86,156m) − 1 = **11.1%** (rounded to one decimal).
- **Fiscal-year total revenue:** $303,154 million for the 52 weeks ended August 30, 2026. It appears in both the release's annual column and the latest 10-K's consolidated statements of income.

Sources: [8-K filing detail and Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/909832/000090983226000084/0000909832-26-000084-index.htm), [Exhibit 99.1 release](https://www.sec.gov/Archives/edgar/data/909832/000090983226000084/costex9918-k92426.htm), [FY2026 10-K filing detail](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html), [FY2026 10-K](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm).

## Reading and viewing list

- Francis & Zhang, [“Can AI match professional analysts?”](https://doi.org/10.1016/j.frl.2026.110127): read the introduction, Section 3.1, and Section 4 through Purdue Libraries.
- Anthropic, [“Building effective agents”](https://www.anthropic.com/research/building-effective-agents): read through “Workflow: Prompt chaining.” A workflow follows a code-fixed path; an agent chooses steps and tools.
- Karpathy, [“Software Is Changing (Again)”](https://www.youtube.com/watch?v=LCEmiRjPEtQ): prompt-as-program and autonomy slider.
- Zhang, [“The Middle Is for the Machine. The Edges Are for You.”](https://cinderzhang.substack.com/p/the-middle-is-for-the-machine-the).
- Karpathy, [post on making model output easier to understand](https://x.com/karpathy/status/2105819303471976479): request prose about 80% of the way to ASD-STE100, then consider diagrams, pages, or videos.

## Before calling Week 1 complete

- Run Codex and Antigravity in Orca with this project folder open. Ask each to create or read a small file, then inspect its work.
- Run the `.env` check and tests above, then use `python3 week01/list_genai_models.py` and `python3 week01/api_smoke_test.py` to verify account access and one live model response.
- Fill `SEC_USER_AGENT` in `.env` with your name and Purdue email before any SEC downloader runs.
- Read the paper sections and watch/read the materials above. Confirm the interpretations aloud with your partner.
- Keep the GitHub repository private until the instructor says to change it. Do not push `.env`.
