"""
Formatters: transform raw backend result dict into display-ready structures.

Each function takes a piece of the result dict and returns either:
  - a markdown string (for gr.Markdown)
  - a pandas DataFrame (for gr.Dataframe)
  - a plain string (for gr.Code / gr.Textbox)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Score display
# ---------------------------------------------------------------------------

# Which direction is "good" for each metric
_SCORE_META = {
    "turn_alignment_score":      {"label": "Turn Alignment",         "higher_is_better": True},
    "repair_score":              {"label": "Repair Score",           "higher_is_better": True},
    "context_honesty_score":     {"label": "Context Honesty",        "higher_is_better": True},
    "continuity_masking_score":  {"label": "Continuity Masking",     "higher_is_better": False},
    "flattery_noise_rate":       {"label": "Flattery Noise Rate",    "higher_is_better": False},
    "monologue_persistence_rate":{"label": "Monologue Persistence",  "higher_is_better": False},
}


def _score_badge(value: float, higher_is_better: bool) -> str:
    """Return a single emoji status badge based on value and direction."""
    if higher_is_better:
        if value >= 0.7:
            return "✅"
        elif value >= 0.4:
            return "⚠️"
        else:
            return "❌"
    else:
        if value <= 0.2:
            return "✅"
        elif value <= 0.5:
            return "⚠️"
        else:
            return "❌"


def _mini_bar(value: float) -> str:
    """Simple 10-char progress bar using block characters."""
    filled = round(value * 10)
    return "█" * filled + "░" * (10 - filled)


def format_scores(scores: Dict[str, float]) -> str:
    """Render score dict as a markdown table with directional badges."""
    lines = [
        "| Metric | Score | | Direction |",
        "|--------|-------|---|-----------|",
    ]
    for key, meta in _SCORE_META.items():
        value = scores.get(key, 0.0)
        badge = _score_badge(value, meta["higher_is_better"])
        bar = _mini_bar(value)
        direction = "↑ higher better" if meta["higher_is_better"] else "↓ lower better"
        lines.append(f"| {meta['label']} | `{bar}` **{value:.2f}** | {badge} | {direction} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Overview panel
# ---------------------------------------------------------------------------

def format_overview(result: Dict[str, Any]) -> str:
    """Render the Overview tab: summary, failure mode, scores."""
    run_id = result.get("run_id", "—")
    case_id = result.get("case_id", "—")
    model = result.get("target_model", "—")
    phase = result.get("phase", "—")
    failure_mode = result.get("failure_mode", "—")
    summary = result.get("summary", "—")
    scores = result.get("scores", {})
    is_mock = result.get("_mock", False)
    num_turns = len(result.get("transcript", []))

    mock_badge = " *(mock data)*" if is_mock else ""

    header = f"""\
## Run Overview{mock_badge}

| Field | Value |
|-------|-------|
| Run ID | `{run_id}` |
| Case | **{case_id}** |
| Model | `{model}` |
| Phase | {phase} |
| Turns | {num_turns} |

---

### Failure Mode

> **{failure_mode}**

{summary}

---

### Scores

"""
    return header + format_scores(scores)


# ---------------------------------------------------------------------------
# Transcript display
# ---------------------------------------------------------------------------

def format_transcript(transcript: List[Dict[str, Any]]) -> str:
    """Render transcript as readable markdown, one block per turn."""
    if not transcript:
        return "*No transcript data.*"

    blocks = []
    for entry in transcript:
        turn_num = entry.get("turn", entry.get("turn_index", "?"))
        user_msg = entry.get("user", entry.get("user_message", "")).strip()
        asst_msg = entry.get("assistant", entry.get("assistant_message", "")).strip()
        action = entry.get("actor_action", "")
        state_before = entry.get("state_before", "")
        state_after = entry.get("state_after", "")

        # Meta line
        meta_parts = []
        if action:
            meta_parts.append(f"`{action}`")
        if state_before and state_after:
            meta_parts.append(f"`{state_before}` → `{state_after}`")
        meta_line = "  ·  ".join(meta_parts) if meta_parts else ""

        block = f"---\n\n**Turn {turn_num}**"
        if meta_line:
            block += f"  ·  {meta_line}"
        block += f"\n\n👤 **User**\n\n> {user_msg}\n\n🤖 **Assistant**\n\n> {asst_msg.replace(chr(10), chr(10) + '> ')}\n"
        blocks.append(block)

    return "\n".join(blocks) + "\n\n---"


# ---------------------------------------------------------------------------
# Turn labels table
# ---------------------------------------------------------------------------

# Friendly column names for display
_LABEL_COLUMNS = [
    ("turn",                   "Turn"),
    ("addressed_current_turn", "Addressed"),
    ("obeyed_scope_constraint","Obeyed Scope"),
    ("monologue",              "Monologue"),
    ("flattery",               "Flattery"),
    ("repair_attempt",         "Repair Attempt"),
    ("fake_repair",            "Fake Repair"),
    ("context_recall",         "Context Recall"),
    ("continuity_masking",     "Continuity Mask"),
]


def _fmt_label_cell(value: Any) -> str:
    """Convert binary label to readable symbol."""
    if value is None:
        return "—"
    return "✓" if int(value) == 1 else "✗"


def format_turn_labels(turn_labels: List[Dict[str, Any]]):
    """
    Return a pandas DataFrame (or list-of-lists fallback) for gr.Dataframe.
    """
    if not turn_labels:
        if _PANDAS_AVAILABLE:
            return pd.DataFrame()
        return []

    col_keys = [k for k, _ in _LABEL_COLUMNS]
    col_headers = [h for _, h in _LABEL_COLUMNS]

    rows = []
    for label in turn_labels:
        row = []
        for key, _ in _LABEL_COLUMNS:
            val = label.get(key)
            if key == "turn":
                row.append(str(val) if val is not None else "?")
            else:
                row.append(_fmt_label_cell(val))
        rows.append(row)

    if _PANDAS_AVAILABLE:
        return pd.DataFrame(rows, columns=col_headers)

    # Fallback: return headers + rows as nested list
    return [col_headers] + rows


# ---------------------------------------------------------------------------
# Debug / raw JSON
# ---------------------------------------------------------------------------

def format_debug(result: Dict[str, Any]) -> str:
    """Return pretty-printed JSON of the full result, safe for display."""
    # Avoid dumping huge fields verbatim — truncate long strings
    def _truncate(obj: Any, max_len: int = 300) -> Any:
        if isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + f"... [{len(obj) - max_len} chars omitted]"
        if isinstance(obj, dict):
            return {k: _truncate(v, max_len) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_truncate(v, max_len) for v in obj]
        return obj

    return json.dumps(_truncate(result), ensure_ascii=False, indent=2)
