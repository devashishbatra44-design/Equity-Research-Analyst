"""Make the single bounded persona call for one saved investor worksheet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .main import run_role


INSTRUCTION = """You are a bounded investor-persona analyst.
Use only the human persona, cited facts, and code-built results supplied in the JSON hand-off.
Do not calculate a number. Do not repeat a number. Refer to evidence only by its fact or calculation ID.
Do not decide liquidity, conviction, a recommendation, or a final release view.
Return exactly three headings: Why the security may be cheap; Why the security may not be cheap; What would change my view.
Under each heading, write one short paragraph. Preserve the human next-filing condition without adding a threshold.
"""


def build_handoff(run: Path) -> dict[str, object]:
    persona = (run / "HUMAN_INVESTOR_PERSONA.md").read_text(encoding="utf-8")
    calculations = json.loads((run / "worksheet_calculations.json").read_text(encoding="utf-8"))
    facts = {
        "F1": "The earnings release states that the issuer requires additional capital to meet obligations and operating needs. Source: earnings release accession 0001213900-26-122794, Updated Asset Values and Liquidity Priorities, saved line 79.",
        "F2": "The earnings release reports a working-capital deficit at the quarter end. Source: earnings release accession 0001213900-26-122794, Balance Sheet and Liquidity, saved line 124.",
        "F3": "The earnings release reports operating cash used for the first nine months of the year. Source: earnings release accession 0001213900-26-122794, Balance Sheet and Liquidity, saved line 124.",
        "F4": "The earnings release reports current and long-term loans payable and related interest. Source: earnings release accession 0001213900-26-122794, Balance Sheet and Liquidity, saved line 125.",
        "F5": "Two ownership reports contained officer or director transaction code P. The saved audit does not characterize them as open-market purchases. Source: ownership_audit.json.",
        "F6": "The proposed merger remains subject to required conditions and approvals. Source: earnings release accession 0001213900-26-122794, Management Commentary, saved line 107.",
    }
    code_results = {
        "C1": f"Course-formula owner cash flow is negative. Saved result: {calculations['owner_cash_flow_usd_millions']} USD millions.",
        "C2": "The human-approved low and mid values are both the zero equity floor because owner cash flow is negative.",
        "C3": "The human-approved low value is below the official close, so the valuation test fails.",
    }
    return {
        "human_persona": persona,
        "facts": facts,
        "code_results": code_results,
        "task": [
            "Explain why the security may be cheap.",
            "Explain why the security may not be cheap.",
            "State the human next-filing condition that would change the view.",
        ],
        "expected_output": (
            "Exactly three Markdown headings with one short paragraph under each. "
            "No calculations, no repeated numbers, no liquidity decision, no conviction, "
            "no recommendation, and no final release view."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    handoff = build_handoff(args.run)
    (args.run / "model_input.md").write_text(
        "# Saved Persona-Call Input\n\n```json\n"
        + json.dumps(handoff, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    output = run_role(
        "Investor Persona",
        INSTRUCTION,
        json.dumps(handoff),
        model="",
        temperature=0.1,
    )
    (args.run / "persona_output.md").write_text(output.strip() + "\n", encoding="utf-8")
    print(args.run / "persona_output.md")


if __name__ == "__main__":
    main()
