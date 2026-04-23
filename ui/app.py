"""
Chatbot Stress Test — Gradio UI

Entry point: python ui/app.py  (run from project root)

Layout:
  Header
  ├── Left panel: controls (model, case, phase, max_turns, temperature, debug, run)
  └── Right panel (tabs):
        Overview  | Transcript | Turn Labels | Report | Debug
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import gradio as gr

# Ensure project root is on sys.path when launched via `python ui/app.py`
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from ui.backend import run_stress_test
from ui.formatters import format_overview, format_transcript, format_turn_labels, format_debug

# ---------------------------------------------------------------------------
# Static options
# ---------------------------------------------------------------------------

MODELS = [
    "anthropic/claude-3.7-sonnet",
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat-v3-0324",
]

CASES = [
    "A01 — Scope Correction (alignment)",
    "B01 — Monologue Under Constraint (structure)",
    "C01 — Context Loss Honesty (continuity)",
    "D01 — Flattery Pollution (alignment)",
]

CASE_ID_MAP = {label: label.split(" ")[0] for label in CASES}

# ---------------------------------------------------------------------------
# Custom CSS — minimal, professional
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
/* Subtle header rule */
.stress-header { border-bottom: 2px solid #e0e0e0; padding-bottom: 12px; margin-bottom: 4px; }

/* Make transcript text a bit more readable */
.transcript-panel .prose { font-size: 0.92rem; line-height: 1.7; }

/* Turn label table: center numeric cells */
.label-table table td { text-align: center; }
.label-table table th { text-align: center; }

/* Status box: monospace, muted */
.status-box textarea { font-family: monospace; font-size: 0.82rem; color: #555; }

/* Run button: full width, prominent */
.run-btn { width: 100% !important; }

/* Score block: slightly larger font */
.score-block .prose { font-size: 0.94rem; }
"""

# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

def handle_run(
    model_label: str,
    case_label: str,
    phase: int,
    max_turns: int,
    temperature: float,
    show_debug: bool,
    strict_real_backend: bool,
) -> Tuple[str, str, str, Any, str, str]:
    """
    Called when the user clicks Run.

    Returns:
      (status, overview_md, transcript_md, labels_df, report_md, debug_str)
    """
    case_id = CASE_ID_MAP.get(case_label, case_label.split(" ")[0])

    try:
        result = run_stress_test(
            target_model=model_label,
            case_id=case_id,
            phase=int(phase),
            max_turns=int(max_turns),
            temperature=float(temperature),
            show_debug=show_debug,
            strict_real_backend=strict_real_backend,
        )
    except Exception:
        err = traceback.format_exc()
        empty_df = format_turn_labels([])
        return (
            f"ERROR\n\n{err}",
            "*Run failed — see status panel.*",
            "*No transcript.*",
            empty_df,
            "*No report.*",
            err,
        )

    # Build status line
    is_mock = result.get("_mock", False)
    fallback_note = ""
    if is_mock:
        reason = result.get("_fallback_reason", "")
        fallback_note = f"\n⚠ Using mock data (real backend unavailable)\n{reason}" if reason else "\n[mock data]"
    status = f"✓ Done  ·  {result.get('run_id', '')} {fallback_note}"

    overview_md  = format_overview(result)
    transcript_md = format_transcript(result.get("transcript", []))
    labels_df    = format_turn_labels(result.get("turn_labels", []))
    report_md    = result.get("report_markdown", "*No report generated.*")
    debug_str    = format_debug(result) if show_debug else "(enable Show Debug to view raw output)"

    return status, overview_md, transcript_md, labels_df, report_md, debug_str


# ---------------------------------------------------------------------------
# Build Gradio app
# ---------------------------------------------------------------------------

def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="Chatbot Stress Test",
        theme=gr.themes.Base(
            primary_hue="slate",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"],
        ),
        css=CUSTOM_CSS,
    ) as demo:

        # ── Header ──────────────────────────────────────────────────────────
        with gr.Column(elem_classes="stress-header"):
            gr.Markdown(
                "# Chatbot Stress Test\n"
                "_Evaluates multi-turn conversational failure modes against target LLMs._  "
                "· Not a general chatbot playground."
            )

        # ── Main layout: left controls + right results ───────────────────────
        with gr.Row(equal_height=False):

            # ── Left: Control Panel ─────────────────────────────────────────
            with gr.Column(scale=1, min_width=260):
                gr.Markdown("### Configuration")

                model_dd = gr.Dropdown(
                    label="Target Model",
                    choices=MODELS,
                    value=MODELS[0],
                )
                case_dd = gr.Dropdown(
                    label="Test Case",
                    choices=CASES,
                    value=CASES[0],
                )
                phase_radio = gr.Radio(
                    label="Phase",
                    choices=[
                        ("2 — Preset turns (fast, no local model)", 2),
                        ("3 — Actor-driven turns",                   3),
                        ("4 — Actor + Judge labels",                 4),
                    ],
                    value=2,
                )
                max_turns_slider = gr.Slider(
                    label="Max Turns",
                    minimum=2,
                    maximum=10,
                    step=1,
                    value=6,
                )
                temp_slider = gr.Slider(
                    label="Temperature",
                    minimum=0.0,
                    maximum=1.0,
                    step=0.05,
                    value=0.2,
                )
                debug_cb = gr.Checkbox(
                    label="Show Debug Output",
                    value=False,
                )
                strict_real_cb = gr.Checkbox(
                    label="Strict Real Backend (no mock fallback)",
                    value=False,
                    info="When enabled, backend errors are shown directly instead of falling back to mock data.",
                )

                run_btn = gr.Button(
                    "▶  Run Stress Test",
                    variant="primary",
                    elem_classes="run-btn",
                )

                status_box = gr.Textbox(
                    label="Run Status",
                    value="Idle",
                    interactive=False,
                    lines=3,
                    elem_classes="status-box",
                )

            # ── Right: Results Panel ────────────────────────────────────────
            with gr.Column(scale=2):
                with gr.Tabs():

                    # Tab A — Overview
                    with gr.Tab("Overview"):
                        overview_md = gr.Markdown(
                            value="_Run a test to see results._",
                            elem_classes="score-block",
                        )

                    # Tab B — Transcript
                    with gr.Tab("Transcript"):
                        transcript_md = gr.Markdown(
                            value="_Run a test to see the transcript._",
                            elem_classes="transcript-panel",
                        )

                    # Tab C — Turn Labels
                    with gr.Tab("Turn Labels"):
                        gr.Markdown(
                            "Each row is one turn. **✓** = label present, **✗** = absent, **—** = N/A."
                        )
                        labels_df = gr.Dataframe(
                            label=None,
                            interactive=False,
                            wrap=False,
                            elem_classes="label-table",
                        )

                    # Tab D — Report
                    with gr.Tab("Report"):
                        report_md = gr.Markdown(
                            value="_Run a test to see the report._",
                        )

                    # Tab E — Debug
                    with gr.Tab("Debug"):
                        debug_out = gr.Code(
                            label="Raw JSON Output",
                            language="json",
                            value="(enable Show Debug and run to view)",
                            interactive=False,
                        )

        # ── Event wiring ────────────────────────────────────────────────────
        run_btn.click(
            fn=handle_run,
            inputs=[model_dd, case_dd, phase_radio, max_turns_slider, temp_slider, debug_cb, strict_real_cb],
            outputs=[status_box, overview_md, transcript_md, labels_df, report_md, debug_out],
        )

    return demo


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = build_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        share=False,
    )
