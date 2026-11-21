"""Run the numeric verifier on every saved live worksheet in the repository."""

from __future__ import annotations

import sys
from pathlib import Path

from .numeric_hook import REFUSAL, verify_file


def main() -> None:
    repository = Path.cwd()
    paths = sorted(repository.glob("week*/runs/**/worksheet.json"))
    errors: list[str] = []
    for path in paths:
        result = verify_file(path)
        errors.extend(f"{path}: {error}" for error in result.errors)
    if errors:
        print(REFUSAL, file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
