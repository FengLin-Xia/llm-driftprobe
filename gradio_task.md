# Chatbot Stress Test Gradio UI Task

## Goal

Build a Gradio-based demo UI for my chatbot stress test project.

This is **not** a generic chatbot app. It is a **stress test / evaluation console** for running predefined multi-turn cases against target models, then displaying:

- the transcript
- turn-level labels
- aggregated scores
- a short failure-mode summary

The UI should be designed for:
1. local debugging
2. demo / interview presentation
3. future extension

Please prioritize:
- clean architecture
- readability
- minimal but solid UX
- code that is easy to extend later

---

## Tech Constraints

- Use **Python**
- Use **Gradio Blocks**, not Interface
- Keep the UI implementation separate from the evaluation logic
- Do **not** rewrite the core runner logic if avoidable
- Wrap existing backend logic with a thin UI layer
- Make the app runnable locally with a simple command

---

## Project Context

I already have or plan to have these backend concepts:

- `case spec`
- `runner`
- `actor`
- `judge`
- `scorer`
- `report generator`

The UI should assume there is a single backend entry function like:

```python
run_stress_test(
    target_model: str,
    case_id: str,
    max_turns: int,
    temperature: float,
    show_debug: bool = False,
) -> dict

And this function should return a structure roughly like:

{
    "run_id": "...",
    "case_id": "...",
    "target_model": "...",
    "summary": "...",
    "scores": {
        "turn_alignment_score": 0.25,
        "repair_score": 0.33,
        "context_honesty_score": 0.0,
        "continuity_masking_score": 0.17,
        "flattery_noise_rate": 0.0,
        "monologue_persistence_rate": 0.17
    },
    "failure_mode": "Defensive Clarification Loop",
    "transcript": [
        {
            "turn": 0,
            "user": "...",
            "assistant": "...",
            "state_before": "S0",
            "state_after": "S1",
            "actor_action": "explicit_correction"
        }
    ],
    "turn_labels": [
        {
            "turn": 0,
            "addressed_current_turn": 0,
            "obeyed_scope_constraint": 0,
            "monologue": 0,
            "flattery": 0,
            "repair_surface": 1,
            "repair_task_level": 0,
            "continuity_masking": 0
        }
    ],
    "report_markdown": "..."
}

If my actual backend function does not exist yet, create a clean mock version so the UI can still run.

UI Requirements

Build a Gradio app with this structure:

1. Header

At the top:

Title: Chatbot Stress Test
Short description:
this tool evaluates multi-turn conversational failure modes
it is not a general chatbot playground
2. Left Control Panel

Inputs:

target model dropdown
case dropdown
max turns slider or number input
temperature slider
show debug checkbox
run button

Optional:

a small textbox showing current run status
3. Right Main Panel

Use tabs or clearly separated sections.

Tab A: Overview

Show:

short run summary
failure mode name
score summary in a compact readable form
Tab B: Transcript

Show the multi-turn transcript in a readable way.
Each turn should clearly show:

turn index
user message
assistant message

If possible, also show:

actor action
state before / after

Make this readable, not raw JSON spam.

Tab C: Turn Labels

Show turn-level labels in a table.
Use a dataframe-like display.
Each row = one turn.

Tab D: Report

Render markdown output from report_markdown.

4. Optional Debug Section

If show_debug=True, show raw JSON outputs or internal metadata in a collapsible area.

UX Requirements
The layout should feel like an evaluation console, not a toy chat app
Keep styling minimal and professional
Avoid clutter
Make transcript the core visualization, not an afterthought
The result should be easy to demo during an interview
Architecture Requirements

Please structure the code cleanly.

Suggested files:

ui/
  app.py
  components.py
  formatters.py
  mock_backend.py
Responsibilities
app.py
creates Gradio Blocks app
wires events
launches app
components.py
reusable UI builders if needed
formatters.py
transform backend result dict into display-friendly structures
examples:
transcript -> markdown or html blocks
turn_labels -> dataframe
scores -> concise summary markdown
mock_backend.py
fallback mock implementation of run_stress_test()
used if real backend is not available

Do not put all logic into one giant file unless absolutely necessary.

Behavior Requirements

When user clicks Run:

collect all input values
call run_stress_test(...)
update:
overview summary
transcript
turn label table
report markdown
fail gracefully if backend errors

Add reasonable error handling.

Formatting Requirements
Score Display

Please display the scores in a clean summary block, for example:

turn_alignment_score
repair_score
context_honesty_score
continuity_masking_score
flattery_noise_rate
monologue_persistence_rate

You may present them as:

markdown list
compact table
simple visual emphasis

No complicated chart is required in v1.

Transcript Display

Make transcript readable.
Prefer a structured format such as:

Turn 0
User
Assistant
Meta info

Instead of dumping raw dicts.

Turn Label Table

Show all available label columns.
If some columns are missing, handle gracefully.

Implementation Strategy

Please do this in order:

Step 1

Create a working mock backend and run the Gradio app with fake data.

Step 2

Build the full UI layout and wire all outputs.

Step 3

Add formatting helpers so the UI looks clean.

Step 4

Make it easy to swap mock backend with real backend later.

Deliverables

Please generate:

all required Python files
a requirements.txt
a short README.md that explains:
how to install
how to run
where to replace mock backend with real logic
Output Style

When coding:

prefer clarity over cleverness
add comments where helpful
keep function boundaries clean
avoid unnecessary framework complexity
Important Notes
Do not overengineer
Do not build a full production product
Build a strong local demo / prototype
The main goal is to present the stress test pipeline clearly

If the backend contract needs slight adjustment for UI friendliness, make a reasonable proposal and implement it consistently.

## Execution Notes for Coding Agent

Please do not overengineer.
Implement a clean local demo first.
Prefer simple, readable Gradio Blocks code over abstraction-heavy patterns.
Before writing code, first propose the file structure and event wiring plan.
Then implement step by step.