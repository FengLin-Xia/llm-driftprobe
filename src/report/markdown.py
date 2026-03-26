from __future__ import annotations

from pathlib import Path
from typing import Dict

from ..scorer.metrics import compute_case_metrics


def render_markdown_report(run_result: Dict) -> str:
    metrics = compute_case_metrics(run_result.get("turn_labels", []))

    lines = [
        f"Target Model: {run_result['model']}",
        f"Case: {run_result['case_id']}",
        f"Status: {run_result['status']}",
        f"Turns: {run_result.get('turn_count', 0)}",
        "",
        f"turn_alignment_score: {metrics['turn_alignment_score']:.2f}",
        f"repair_score: {metrics['repair_score']:.2f}",
        f"context_honesty_score: {metrics['context_honesty_score']:.2f}",
        f"continuity_masking_score: {metrics['continuity_masking_score']:.2f}",
        f"flattery_noise_rate: {metrics['flattery_noise_rate']:.2f}",
        f"monologue_persistence_rate: {metrics['monologue_persistence_rate']:.2f}",
    ]

    transcript = run_result.get("transcript") or []
    if transcript:
        lines.append("")
        lines.append("Transcript (debug, truncated):")
        for t in transcript:
            turn_index = t.get("turn_index", "?")
            user_message = (t.get("user_message") or "").replace("\n", " ").strip()
            assistant_message = (t.get("assistant_message") or "").replace("\n", " ").strip()

            # 避免 report 过长：每条消息最多展示 220 字符
            user_short = user_message[:220] + ("..." if len(user_message) > 220 else "")
            assistant_short = assistant_message[:220] + ("..." if len(assistant_message) > 220 else "")

            lines.append(f"- Turn {turn_index} - user: {user_short}")
            lines.append(f"- Turn {turn_index} - assistant: {assistant_short}")

    return "\n".join(lines)


def save_markdown_report(run_result: Dict, path: Path) -> None:
    content = render_markdown_report(run_result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

