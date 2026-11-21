#!/bin/zsh
set -eu

task_script_dir=${0:A:h}
task_repo_root=${task_script_dir:h}

cd "$task_repo_root"
PYTHONPATH=equity_research_crewai/src \
  .venv/bin/python -m equity_research_crewai.numeric_hook_runner
