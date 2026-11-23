"""Extract worksheet inputs from saved filing text and frozen non-model sources."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}.")
    return value


def _number(value: str) -> Decimal:
    cleaned = re.sub(r"[^0-9.\-]", "", value.replace(",", ""))
    if not cleaned:
        raise ValueError(f"No numeric value in {value!r}.")
    return Decimal(cleaned)


def extract(
    run: Path,
    spec: Mapping[str, Any],
    config: Mapping[str, Any],
    market: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Extract configured filing facts and join frozen human and market inputs."""

    inputs: dict[str, str] = {}
    evidence: dict[str, Any] = {"facts": []}
    facts = spec.get("facts", [])
    if not isinstance(facts, list):
        raise ValueError("Extraction spec facts must be a list.")
    for item in facts:
        if not isinstance(item, Mapping):
            raise ValueError("Each extraction fact must be an object.")
        fact_id = str(item["id"])
        source_file = str(item["source_file"])
        start = int(item["line_start"])
        end = int(item["line_end"])
        if start < 1 or end < start:
            raise ValueError(f"Invalid line range for {fact_id}.")
        source_path = (run / source_file).resolve()
        if run.resolve() not in source_path.parents:
            raise ValueError(f"Source escapes the run folder: {source_file}")
        lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        chunk = "\n".join(lines[start - 1 : end])
        match = re.search(str(item["pattern"]), chunk, flags=re.IGNORECASE | re.DOTALL)
        if match is None:
            raise ValueError(f"Pattern did not match {fact_id} in {source_file}:{start}-{end}.")
        raw = match.group(int(item.get("group", 1))).strip()
        source_line = start
        for offset, source_line_text in enumerate(lines[start - 1 : end]):
            if raw in source_line_text:
                source_line = start + offset
                break
        value_type = str(item.get("value_type", "number"))
        if value_type == "number":
            value = _number(raw)
            value *= Decimal(str(item.get("multiplier", "1")))
            if item.get("negate") is True:
                value = -value
            rendered = format(value, "f")
        elif value_type in {"text", "date"}:
            rendered = re.sub(r"\s+", " ", raw)
        else:
            raise ValueError(f"Unsupported value_type {value_type!r} for {fact_id}.")
        inputs[fact_id] = rendered
        evidence["facts"].append(
            {
                "id": fact_id,
                "value": rendered,
                "unit": item["unit"],
                "period": item["period"],
                "form": item["form"],
                "accession": item["accession"],
                "section": item["section"],
                "source_file": source_file,
                "saved_lines": f"{start}-{end}",
                "source_line": source_line,
                "source_token": raw,
                "source_multiplier": str(item.get("multiplier", "1")),
                "pattern": item["pattern"],
                "value_type": value_type,
            }
        )

    for output_key, config_key in dict(spec.get("human_inputs", {})).items():
        inputs[str(output_key)] = str(config[str(config_key)])
    for output_key, market_key in dict(spec.get("market_inputs", {})).items():
        inputs[str(output_key)] = str(market[str(market_key)])
    for output_key, value in dict(spec.get("constants", {})).items():
        inputs[str(output_key)] = str(value)

    evidence["human_input_keys"] = dict(spec.get("human_inputs", {}))
    evidence["market_input_keys"] = dict(spec.get("market_inputs", {}))
    evidence["constants"] = dict(spec.get("constants", {}))
    return inputs, evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence-output", required=True, type=Path)
    args = parser.parse_args()
    inputs, evidence = extract(
        args.run,
        _load(args.spec),
        _load(args.config),
        _load(args.market),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inputs, indent=2) + "\n", encoding="utf-8")
    args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
