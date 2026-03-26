# Chatbot Stress Test — Gradio UI

A local evaluation console for running predefined multi-turn stress test
cases against target LLMs and visualizing transcripts, turn-level labels,
and aggregated failure-mode scores.

---

## Install

From the project root (`D:\chatbot_stress_test`):

```bash
pip install gradio pandas
# or install everything:
pip install -r requirements.txt
```

---

## Run

```bash
# From the project root:
python ui/app.py
```

Open `http://127.0.0.1:7860` in your browser.

---

## What you see

| Tab | Content |
|-----|---------|
| **Overview** | Run summary, failure mode, score table with directional badges |
| **Transcript** | Turn-by-turn conversation with actor action & state transitions |
| **Turn Labels** | Binary label table (✓/✗) produced by the Judge |
| **Report** | Full markdown report |
| **Debug** | Raw JSON output (enable "Show Debug" checkbox first) |

---

## Mock vs Real backend

The UI ships with a **mock backend** (`ui/mock_backend.py`) that returns
pre-written realistic data for each of the 4 test cases (A01–D01).

The app automatically tries the **real backend** first. If anything fails
(missing API key, local model not loaded, etc.), it falls back to mock
and shows a warning in the status panel.

### To use the real backend

1. Set `OPENROUTER_API_KEY` in `.env` at the project root.
2. For Phase 3/4: ensure `configs/models.yaml` points to a valid local model.
3. Select **Phase 2** (fastest, no local model needed) to start.

### To always use mock data

Edit `ui/backend.py` and replace the `try` block with a direct call to
`mock_backend.run_stress_test(...)`.

---

## Phases

| Phase | What runs | Requires |
|-------|-----------|----------|
| 2 | Fixed preset user turns (A01 only) | OpenRouter API key |
| 3 | Actor-generated user turns | API key + local Qwen2.5-7B |
| 4 | Actor + Judge labels | API key + local Qwen2.5-7B |

---

## File structure

```
ui/
  app.py           — Gradio Blocks app, event wiring, launch
  backend.py       — Real backend bridge + mock fallback
  formatters.py    — Result dict → display-ready markdown / DataFrames
  mock_backend.py  — Standalone mock run_stress_test() with realistic data
  README.md        — This file
```
