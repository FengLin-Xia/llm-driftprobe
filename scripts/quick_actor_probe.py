from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.actor.engine import ActorConfig, ActorEngine
from src.adapters.router import build_adapters_from_config
from src.runner.run_case import load_case_spec


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quick actor-only probe (no target API call).",
    )
    parser.add_argument("--case-id", default="D01", help="Case ID: A01/B01/C01/D01")
    parser.add_argument("--turns", type=int, default=2, help="How many actor turns to sample")
    parser.add_argument(
        "--assistant-placeholder",
        default="收到，继续。",
        help="Placeholder assistant text fed back into transcript.",
    )
    return parser.parse_args()


async def run_probe(case_id: str, turns: int, assistant_placeholder: str) -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    case_spec = load_case_spec(root / "cases", case_id)
    adapters = build_adapters_from_config(str(root / "configs" / "models.yaml"))

    if "local/transformers" not in adapters:
        raise RuntimeError("Missing local/transformers adapter. Check configs/models.yaml.")

    actor = ActorEngine(
        adapters["local/transformers"],
        ActorConfig(model=case_spec.get("actor_model", "local")),
    )

    transcript: List[Dict[str, Any]] = []
    current_state = case_spec["initial_state"]
    rows: List[Dict[str, Any]] = []

    n_turns = max(1, int(turns))
    for i in range(n_turns):
        out = await actor.choose_action_and_utterance(
            case_spec=case_spec,
            transcript=transcript,
            current_state=current_state,
        )

        user_message = (out.get("user_message") or "").strip()
        row = {
            "turn": i,
            "state_before": current_state,
            "state_after": out.get("state", current_state),
            "chosen_action": out.get("chosen_action"),
            "user_message": user_message,
            "actor_meta": out.get("_actor_meta", {}),
        }
        rows.append(row)

        transcript.append(
            {
                "turn_index": i,
                "state_before": current_state,
                "state_after": row["state_after"],
                "actor_action": row["chosen_action"],
                "user_message": user_message,
                "assistant_message": assistant_placeholder,
            }
        )
        current_state = row["state_after"]

    unique_messages = sorted({r["user_message"] for r in rows if r["user_message"]})
    return {
        "case_id": case_id,
        "turns": n_turns,
        "unique_user_messages": len(unique_messages),
        "rows": rows,
    }


async def main() -> None:
    args = parse_args()
    result = await run_probe(args.case_id, args.turns, args.assistant_placeholder)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
