# Week 5 Replay and Reproducibility Review

Reviewer: Jeenay Vipul Dedhia (`jeenaydedhia`), replay and reproducibility reviewer.

Issue: #5

Review date: November 26, 2026.

Base commit: `main` at `b4a4faaaf3573bc5dbc775434a466f01085a8936`. Review branch `review/week5-jeenay-replay` was created from that commit.

Status: **BLOCKED for the Lab 09 replay.** The two partner-selected Lab 09 run folders do not exist on `main` yet, so I have not replayed them and do not report that replay as complete. To have the method ready, I proved it on the two committed live runs, WFCF (Week 4) and SUNE (Week 5). Those results are in section 4.

## 1. What Issue #5 asks, and where each item stands

| Requirement | Status |
|---|---|
| Replay both partner-selected Lab 09 runs from saved files | **Blocked.** No Lab 09 run folder exists on `main`. |
| Confirm the replay makes no new network fetch | Method ready and proved on WFCF and SUNE: 0 network attempts (section 3). |
| Confirm a separate dated folder and report for each ticker | Method ready: each replay writes `<TICKER>_<YYYYmmdd_HHMMSS>_reverify/` with its own report (section 4). |
| Compare replay reports with the original reports | Done for WFCF and SUNE (section 4). Lab 09 pending. |
| Record the command, file paths, and report hashes | Done for WFCF and SUNE (sections 3 and 4). Lab 09 pending. |

## 2. Why a new replay tool was needed

Lab 08 asks for "the exact command to replay a saved run without fetching anything." I checked the commands that exist on `main`:

- `python -m equity_research_crewai.main TICKER --saved-run RUN` creates a new dated folder, but it calls the model for every role. Without `--price`, it also runs `curl` to `api.nasdaq.com`. It is not an offline replay.
- `week02/desk_app.py --saved-run RUN --reuse-role-outputs` still calls the model for the Advisor and Manager, and it writes into `RUN`.
- `python -m equity_research_crewai.main --verify-only RUN` tries one model call, then falls back to code checks, and writes into `RUN` itself.
- `week02/report_provenance.py RUN` is offline, but it only checks. It creates no output folder.

None of these both avoids the network and keeps a separate dated folder per ticker. I added `week05/team_reviews/review_tools/`:

- `reverify_saved_runs.py` copies each saved run, including its original `report.md`, to `<REPLAY_ROOT>/<TICKER>_<YYYYmmdd_HHMMSS>_reverify/`. It reruns only the code-based Verifier (`verify_saved_run`, no model) in the copy. It then compares hashes and code marks with the original. It never writes into the original folder. It exits 0 when the code marks match and 1 when they differ.
- `netguard/sitecustomize.py` logs and refuses every Python socket connection and DNS lookup.
- `netguard_bin/curl` and `netguard_bin/wget` log and refuse any download started as a subprocess. The desk calls `curl` that way in `closes_reader.py`.

The tool is a review aid. It does not change any desk code.

## 3. Commands

Setup: the same fresh clone and `.venv` as my Issue #2 review (macOS 26.5.1, arm64, Python 3.12.8, `crewai` 1.9.3, `pip check` clean).

Each replay runs the Verifier code from the commit that published the run, using a detached worktree, so that later code changes cannot change the result:

```bash
git worktree add --detach ../pin_wfcf_0cce0fe 0cce0fe   # commit that published WFCF
git worktree add --detach ../pin_sune_f2d0bf4 f2d0bf4   # commit that published SUNE

T=$PWD/week05/team_reviews/review_tools
export NETGUARD_LOG=~/FIN67110/replay_out/netguard.log
export PATH="$T/netguard_bin:$PATH" PYTHONPATH="$T/netguard"

cd ../pin_sune_f2d0bf4
../Equity-Research-Analyst/.venv/bin/python $T/reverify_saved_runs.py --repo . \
  --replay-root ~/FIN67110/replay_out/pinned \
  week05/runs/live/SUNE_20261121_022515=verifier_output_final.json

cd ../pin_wfcf_0cce0fe
../Equity-Research-Analyst/.venv/bin/python $T/reverify_saved_runs.py --repo . \
  --replay-root ~/FIN67110/replay_out/pinned \
  week04/runs/live/WFCF_20261114_144628=verifier_output.json
```

I also ran both runs against `b4a4faa` (current `main`) and WFCF against `a1b6fbe` (the parent of `0cce0fe`).

Network proof:

- Guard self-test before the replays: `urllib` to `https://www.sec.gov` raised `URLError`, and `curl https://example.com` exited 7. The guard works.
- During every replay, `netguard.log` stayed at **0 lines**. No socket, DNS, `curl`, or `wget` attempt was made.

Offline consistency check:

```bash
.venv/bin/python week02/report_provenance.py week04/runs/live/WFCF_20261114_144628
.venv/bin/python week02/report_provenance.py week05/runs/live/SUNE_20261121_022515
```

## 4. Results on the committed live runs

| | SUNE | WFCF |
|---|---|---|
| Original folder | `week05/runs/live/SUNE_20261121_022515` | `week04/runs/live/WFCF_20261114_144628` |
| Code pinned to | `f2d0bf4` | `0cce0fe` |
| Replay folder | `SUNE_20261126_202525_reverify` | `WFCF_20261126_202525_reverify` |
| Original `report.md` SHA-256 | `7badb652a8775797cf41598600e39e8b36eca2c831330367825f4e3901c78c89` | `bd980331293bf469618afbadb47c438480b298a9be2bf715beaa5f07fd8718d3` |
| `report.md` in replay folder | identical | identical |
| Original verifier output | `verifier_output_final.json` `5256036f…79d0` | `verifier_output.json` `cfecf215…be83` |
| Replay verifier output | `dabb8ec719cf8c1c0a633762afb4662bd3e360f7a0662d25e9dad232b4c808a8` | `3988b61ef496fe3db56ee002224f3bd87f6a00c75f40a5ceaf6fae315d00a905` |
| Replay verified report | `c1961a07aa25ba9267707795c770e35cd6394ecf50d88a0c527997a115fc9f47` | `ee602f987b2dda926608a2a8052d15496700221de95113f53649f74d53bbe0ea` |
| Code marks | **29 of 29 identical** | **16 of 81 differ** |
| Network attempts | 0 | 0 |
| `report_provenance.py` | **FAIL**: report differs from saved role outputs | **FAIL**: report differs from saved role outputs |

The verifier output file hashes differ even when the marks match, because the replay file has its own timestamps and paths. The comparison that matters is the code marks.

Repeat run: a second SUNE replay into a new folder (`SUNE_20261126_202603_reverify`) produced the same verifier-output and verified-report hashes. The replay is deterministic.

The original folders were unchanged: `git status --short` was empty in both pinned worktrees after the replays.

### SUNE

The saved verifier marks reproduce exactly when the code is pinned to `f2d0bf4`. At `b4a4faa`, 2 of 29 entries differ in text only; both stay "Unsupported". This is the expected effect of verifier changes after the run.

### WFCF

The saved code marks do **not** reproduce from committed code:

- At `0cce0fe` (the commit that published WFCF): 16 of 81 entries differ. 6 change from Unsupported to Correct, 2 from Wrong to Correct, and 8 keep their mark but differ in text.
- At `a1b6fbe` (the parent commit): 15 of 81 differ.
- At `b4a4faa` (current `main`): the same 16 of 81 differ.

So the committed WFCF `verifier_output.json` was produced by Verifier code that is not in any commit I tested. I do not know which code produced it. Only Devashish can say.

## 5. Findings for the team

1. **Both live reports fail the repository's own provenance check.** `report_provenance.py` prints FAIL for WFCF and SUNE: `report.md` does not match `role_outputs.json`. For SUNE, the saved node records show the Investment Advisor recommended **Sell**, and `manager_review.json` has status `failed_after_one_retry`. The committed report states no Buy, Hold, or Sell. The README calls `report.md` immutable desk output. Devashish should explain where the published text came from and disclose it in the report.
2. **The committed WFCF verifier marks cannot be reproduced from committed code** (section 4).
3. **`main --saved-run` is not an offline replay.** It calls the model and `api.nasdaq.com`. For Lab 08 and Lab 09, the team should either adopt a code-only replay command like the one in this review, or document that only the Verifier stage replays offline.
4. **Filing text under `week02/runs/` is ignored by Git.** `.gitignore` line 69 ignores `week02/runs/**/*.txt`. Live runs under `week04/` and `week05/` are not affected. Any Lab 09 run folder must keep `10-k.txt`, `10-q.txt`, `8-k.txt`, and `exhibit-99-1.txt` committed, or a fresh clone cannot replay it.
5. **`week05/FINAL_AUDIT.md` is out of date.** It reports PASS, 183 tests, and an unpushed commit. Current `main` has 193 tests and the commit is pushed, and finding 1 is not mentioned.

## 6. What I need before the Lab 09 replay can finish

1. The two partner-selected tickers. The partner must be from another team, the companies must have reported in the past 30 days, and at least one must come from the build-out set.
2. Both run folders committed to `main` with their filing text, and the commit hash.
3. Then I will run, for each folder:

```bash
git worktree add --detach ../pin_lab09 <COMMIT>
cd ../pin_lab09
../Equity-Research-Analyst/.venv/bin/python $T/reverify_saved_runs.py --repo . \
  --replay-root ~/FIN67110/replay_out/lab09 \
  <RUN1>=<verifier output file> <RUN2>=<verifier output file>
../Equity-Research-Analyst/.venv/bin/python week02/report_provenance.py <RUN1> <RUN2>
```

I will mark Issue #5 complete only if all of these hold for both runs: the network log has 0 lines, the code marks are identical, each ticker has its own dated replay folder and report, and the original folders are unchanged. Otherwise I will record the failure here.

## 7. Conclusion

- **Lab 09 replay: blocked.** The partner-selected runs do not exist yet.
- **Replay method: ready.** It is offline (0 network attempts), keeps one dated folder and report per ticker, leaves originals unchanged, and is deterministic.
- **SUNE: reproducible** at its publishing commit, but it fails the provenance check.
- **WFCF: not reproducible** from committed Verifier code, and it fails the provenance check.

This is a learning exercise, not financial advice.

AI assistance: Claude (Anthropic). I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
