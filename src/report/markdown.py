from __future__ import annotations

from pathlib import Path
from typing import Dict

from ..scorer.metrics import compute_case_metrics


def render_markdown_report(run_result: Dict) -> str:
    case_spec = run_result.get("case_spec", {}) or {}
    extension_metrics = case_spec.get("extension_metrics", []) or []
    metrics = compute_case_metrics(run_result.get("turn_labels", []), extension_metrics=extension_metrics)

    lines = [
        f"Target Model: {run_result['model']}",
        f"Case: {run_result['case_id']}",
        f"Status: {run_result['status']}",
        f"Turns: {run_result.get('turn_count', 0)}",
        "",
    ]

    phenomenon = case_spec.get("phenomenon")
    seed_scenario = case_spec.get("seed_scenario")
    observation_focus = case_spec.get("observation_focus")
    transition_windows = case_spec.get("transition_windows", []) or []

    if phenomenon or seed_scenario or observation_focus:
        lines.extend(["Phenomenon Summary:", ""])
        if phenomenon:
            lines.append(f"- phenomenon: {phenomenon}")
        if seed_scenario:
            lines.append(f"- seed_scenario: {seed_scenario}")
        if observation_focus:
            lines.append(f"- observation_focus: {observation_focus}")
        lines.append("")

    lines.extend(
        [
            f"turn_alignment_score: {_format_metric(metrics.get('turn_alignment_score'))}",
            f"repair_score: {_format_metric(metrics.get('repair_score'))}",
            f"context_honesty_score: {_format_metric(metrics.get('context_honesty_score'))}",
            f"continuity_masking_score: {_format_metric(metrics.get('continuity_masking_score'))}",
            f"flattery_noise_rate: {_format_metric(metrics.get('flattery_noise_rate'))}",
            f"monologue_persistence_rate: {_format_metric(metrics.get('monologue_persistence_rate'))}",
        ]
    )

    if extension_metrics:
        lines.extend(["", "Extension Metrics:"])
        for name in extension_metrics:
            lines.append(f"- {name}: {_format_metric(metrics.get(name))}")

    if transition_windows:
        lines.extend(["", "Transition Windows:"])
        for window in transition_windows:
            if not isinstance(window, dict):
                continue
            from_turn = window.get("from_turn", "?")
            to_turn = window.get("to_turn", "?")
            focus = window.get("focus", window.get("observation_focus", ""))
            lines.append(f"- Turn {from_turn} -> {to_turn}: {focus}")

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


def _format_metric(value: object) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "n/a"


def save_markdown_report(run_result: Dict, path: Path) -> None:
    content = render_markdown_report(run_result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

