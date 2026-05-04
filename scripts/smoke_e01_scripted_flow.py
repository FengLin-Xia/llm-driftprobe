from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adapters.base import BaseChatAdapter, ChatRequest, ChatResponse
from src.report.markdown import render_markdown_report
from src.runner import run_case as rc
from src.runner.run_case import RunConfig


class FakeAdapter(BaseChatAdapter):
    provider_name = "fake/local"
    model_name = "fake-target"

    async def chat(self, request: ChatRequest, *, timeout: Optional[float] = None) -> ChatResponse:
        last_user = [m["content"] for m in request["messages"] if m.get("role") == "user"][-1]
        return ChatResponse(
            provider=self.provider_name,
            model=request["model"],
            content="FAKE_TARGET_RESPONSE: " + last_user[:80],
        )


async def main() -> None:
    rc.build_adapters_from_config = lambda path: {"fake/local": FakeAdapter()}

    result = await rc.run_single_case(
        RunConfig(case_id="E01", provider="fake/local", model="fake-target", phase=2)
    )

    transition_count = len([o for o in result["observations"] if o.get("unit") == "transition"])
    report = render_markdown_report(result)

    assert result["status"] == "scripted_case_completed"
    assert result["turn_count"] == 3
    assert len(result["transcript"]) == 3
    assert transition_count == 2
    assert "Phenomenon Summary" in report
    assert "Transition Windows" in report

    print("E01 scripted flow smoke: OK")
    print(f"status: {result['status']}")
    print(f"turn_count: {result['turn_count']}")
    print(f"transition_observations: {transition_count}")
    for entry in result["transcript"]:
        user_message = entry["user_message"]
        ascii_user = user_message.encode("unicode_escape").decode("ascii")
        print(f"turn{entry['turn_index']}_user_len: {len(user_message)}")
        print(f"turn{entry['turn_index']}_user_escaped: {ascii_user}")


if __name__ == "__main__":
    asyncio.run(main())
