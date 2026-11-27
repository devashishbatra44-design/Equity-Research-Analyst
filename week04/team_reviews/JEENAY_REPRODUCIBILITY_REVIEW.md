# Week 4 Independent Reproducibility and Verifier Review

Reviewer: Jeenay Vipul Dedhia (`jeenaydedhia`)

Issue: #2

Review date: November 26, 2026.

Fresh-clone source: `https://github.com/devashishbatra44-design/Equity-Research-Analyst.git`, cloned into a new, empty directory on my own machine. I did not use any file, `.venv`, or `.env` from Devashish's machine.

Base commit: `main` at `b4a4faaaf3573bc5dbc775434a466f01085a8936` ("fix(week4): complete audited seeker and worksheet remediation", November 23, 2026).

Review branch: `review/week4-jeenay-reproducibility`, created from that exact commit.

Conclusion: **Reproducible with limitations.** The suite, the clean hook, and the seeded-copy refusal all reproduce. The documented launcher `./week04/run_numeric_hook.sh` does not run as written, and the restricted-data check found licensed and raw market data in history and one licensed value at HEAD. Details are in sections 7 and 8.

## 1. Environment

- Operating system: macOS 26.5.1 (build 25F80), Apple silicon (arm64).
- Python 3.12.8 in a new virtual environment created for this review.
- `crewai` 1.9.3, `openai` 1.83.0, `pytest` 8.4.2.
- `pip install -r week02/requirements.txt`: exit 0.
- `pip install -e equity_research_crewai`: exit 0.
- `pip check`: "No broken requirements found."
- No `.env` file, no API key, no raw close list, and no Capital IQ or LSEG export were present or needed.

## 2. Setup commands

```bash
mkdir -p ~/FIN67110 && cd ~/FIN67110
gh repo clone devashishbatra44-design/Equity-Research-Analyst
cd Equity-Research-Analyst
git remote -v          # origin = devashishbatra44-design/Equity-Research-Analyst
git rev-parse HEAD     # b4a4faaaf3573bc5dbc775434a466f01085a8936
git switch -c review/week4-jeenay-reproducibility b4a4faa
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r week02/requirements.txt
.venv/bin/python -m pip install -e equity_research_crewai
.venv/bin/python -m pip check
```

## 3. Full offline test suite

Command, from the repository root, as `README.md` line 29 documents it:

```bash
PYTHONPATH=.:week01 .venv/bin/python -m pytest -q
```

Result: **193 passed in 33.30 seconds.** No failures and no errors.

## 4. Clean numeric hook

Command as Issue #2 and `week04/README.md` name it:

```bash
./week04/run_numeric_hook.sh; echo "exit=$?"
```

Result: **exit 126, `permission denied`.** The file is tracked with mode `100644`, so it is not executable in a fresh clone.

Command as `.codex/hooks.json` line 8 actually calls it:

```bash
zsh week04/run_numeric_hook.sh; echo "exit=$?"
```

Result: **exit 0, no output (0 bytes).** The hook is silent on the clean worksheets.

The runner checks every `week*/runs/**/worksheet.json` in the repository. On this commit that is:

- `week04/runs/worksheet_FDXF_20261120_023851/worksheet.json`
- `week05/runs/live/SUNE_20261121_022515/worksheet.json`

## 5. Seeded-copy test

```bash
PYTHONPATH=.:week01 .venv/bin/python -m pytest -q \
  "equity_research_crewai/tests/test_numeric_hook.py::test_seeded_copy_of_saved_worksheet_is_refused"
```

Result: **1 passed in 0.03 seconds.**

What the test does (`test_numeric_hook.py` lines 52 to 63):

- It copies `week04/runs/worksheet_FDXF_20261120_023851` into pytest's temporary directory.
- It changes only the copy's `worksheet.md`, replacing `= 725 USD millions` with `= 726 USD millions`.
- It runs `verify_file` on the copy and asserts that the result is not `ok` and names a worksheet or token error.

I also ran the same seed by hand on a copy in a temporary directory, so I could read the refusal text:

```text
ok= False
REFUSE: saved worksheet numeric verification failed
L051_T01: token is absent from the saved worksheet line
worksheet line 51: unclassified numeric token '726'
```

The refusal is useful. It names the claim ID, the worksheet line, and the token that does not belong. The incorrect copy cannot be reported as complete.

The original saved worksheet was unchanged. SHA-256 before and after all runs:

| File | Before | After |
|---|---|---|
| `worksheet.md` | `035afa93b810750834289a383689efc5bcc4abd13cc5f45f1dd42b50d784772a` | same |
| `worksheet.json` | `14b3bdd7f5197be129f41d5e4e4fc31e72677d46b9985465ad5c6a13b192edf5` | same |

`git status --short` was empty after all runs.

## 6. Generic-hook review

- `numeric_hook_runner.py` (26 lines) globs `week*/runs/**/worksheet.json` and calls `verify_file` on each path. It does not name a ticker.
- A search of `numeric_hook_runner.py` and `numeric_hook.py` for `FDXF`, `FedEx`, or a fixed `ticker =` found no match.
- `verify_file` reads the saved `worksheet.json` and checks each claim's token against the saved worksheet line. It also recomputes the printed arithmetic, so it checks the saved worksheet itself, not a copy held in the test.
- The FDXF folder name appears only in the test fixture, which is the correct place for it.

Result: **the hook is generic and checks the saved worksheet itself.**

## 7. Secret and restricted-data scan

Secrets:

```bash
git ls-files week04 | xargs grep -nIE \
  "sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|github_pat_|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY|tvly-|xox[bp]-|AIza[0-9A-Za-z_-]{30}|(api[_-]?key|password|secret|token) *[:=] *['\"][^'\"]{8,}"
git ls-files | grep -E '(^|/)\.env'
```

Result: no secret pattern matched. The only tracked environment file is `.env.example`, which holds placeholders.

Restricted data at HEAD:

- No raw close list, raw Nasdaq payload, or licensed export file is tracked under `week04/` at HEAD.
- `week04/runs/seeker_20261119/evidence.md` line 46 quotes one value from a Capital IQ transaction export (a spin-off share price). This is a single licensed data point in a public repository. I did not copy the value into this review.

Restricted data in history (deleted at HEAD by `b4a4faa`, but still public in earlier commits):

| Added in | File |
|---|---|
| `9d2194a` | `week04/runs/worksheet_FDXF_20261120_023851/licensed_close_reader.json` (derived from a Capital IQ export) |
| `9d2194a` | `week04/runs/worksheet_FDXF_20261120_023851/evidence/nasdaq_fdxf_20261009_20261119.json` (raw close list) |
| `f7d90d8` | `week04/runs/live/WFCF_20261114_144628/hit_rate_nasdaq_raw.json` (raw market payload) |
| `f7d90d8` | `week04/runs/live/WFCF_20261114_144628/hit_rate_closes.json` (close list) |

The suite and the hook did not need any of these files.

## 8. Warnings, failures, and limitations

1. **The documented launcher fails in a fresh clone.** `./week04/run_numeric_hook.sh` returns exit 126 because the tracked mode is `100644`. The script also requires `zsh` (`#!/bin/zsh` and `${0:A:h}`), so it will not run on a Linux machine without `zsh`. The Python module it wraps works.
2. **One Capital IQ value at HEAD** in `week04/runs/seeker_20261119/evidence.md` line 46.
3. **Licensed and raw market files remain in public history** (section 7 table).
4. **Local paths in tracked files.** 26 tracked lines contain an absolute `/Users/...` path. These are not secrets.
5. **Saved filing text is ignored for most Week 2 runs.** `.gitignore` ignores `week02/runs/**/*.txt` except four folders allowed back by name. A fresh clone cannot replay those other runs from saved files.
6. **Not reproduced here:** a full desk run, because it needs a model key and network access. Issue #2 does not require one.

## 9. Proposed corrections for Devashish to decide

I did not change any existing Week 4 file.

1. Run `git update-index --chmod=+x week04/run_numeric_hook.sh` and change the launcher to `#!/bin/sh` with a portable repository-root lookup. Alternatively, document `zsh week04/run_numeric_hook.sh` as the command.
2. Replace the Capital IQ figure in `evidence.md` line 46 with a description that does not quote the value.
3. Decide with the instructor whether the licensed and raw files in history need a history rewrite. If not, record the decision.
4. Decide whether live and Lab 09 run folders must force-add their filing text so a fresh clone can replay them.

## 10. Conclusion

**Reproducible with limitations.**

- The full offline suite (193 tests) reproduces on a fresh clone in a new environment.
- The generic hook is silent on the clean worksheets when run the way `.codex/hooks.json` runs it.
- The seeded copy is refused with a useful, line-level error, and the original worksheet is unchanged.
- The documented `./week04/run_numeric_hook.sh` command fails as written.
- The restricted-data check found one licensed value at HEAD and licensed and raw files in history. These need a decision from Devashish.

This is a learning exercise, not financial advice.

AI assistance: Claude (Anthropic). I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
