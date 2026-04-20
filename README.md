# GSentinel — Agentic Benefits Fulfillment Engine

GSentinel is an agentic pipeline that automatically detects, diagnoses, and fixes carrier enrollment rejections — without human intervention for high-confidence corrections.

## How It Works

Carrier rejection notices are fed into a 4-node LangGraph pipeline:

```
Parser → Healer → Critic → Messenger
```

| Node | Role |
|---|---|
| 🔍 **Parser** | Extracts employee ID, error code, and field from the raw carrier rejection text. Looks up the plain-English error description from the knowledge base. |
| 🩺 **Healer** | Looks up the correct value from the internal HR database. Never guesses — only uses authoritative data. |
| ⚖️ **Critic** | Validates the corrected value against the enrollment schema using regex. Sets a confidence score (0.95 = valid, 0.5 = uncertain). |
| 📨 **Messenger** | If confidence ≥ 0.9: auto-fixes and generates a success action card. Otherwise: routes to human review. |

## Quick Start

### 1. Install dependencies

```bash
pip install langgraph fastapi uvicorn
```

### 2. Run the CLI pipeline

```bash
cd gsentinel
python sentinel.py
```

Expected output:
```
✅ Fixed automatically: We corrected a zip code typo in Jordan Smith's enrollment (8020 → 80201). No action needed.
```

### 3. Run the visual web UI

```bash
cd gsentinel
uvicorn api:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

The UI shows:
- Animated pipeline with live node status
- Per-node input/output inspection
- Confidence meter and correction summary
- Full agent trace log

## Project Structure

```
GSentinel/
├── CLAUDE.md                        # Build instructions & hard rules
├── README.md
├── .gitignore
└── gsentinel/
    ├── sentinel.py                  # LangGraph DAG entry point (CLI)
    ├── api.py                       # FastAPI server + static frontend
    ├── graph/
    │   ├── state.py                 # FulfillmentState TypedDict
    │   └── nodes.py                 # 4 agent nodes
    ├── data/
    │   ├── internal_db.json         # Employee HR records (source of truth)
    │   └── knowledge/
    │       └── carrier_errors.md    # Error code reference
    ├── schema/
    │   └── standard_enr.json        # Enrollment validation schema
    ├── mocks/
    │   └── carrier_logs/
    │       └── sample_error.txt     # Sample carrier rejection notice
    ├── frontend/
    │   └── index.html               # Single-page visual workflow app
    └── logs/
        └── agent_trace.json         # Generated at runtime — not committed
```

## Hard Rules

- No external no-code tools (no n8n, Zapier, Make)
- The LLM never guesses a premium, SSN, or financial field — code-only lookups
- Every auto-fix must pass schema validation before being accepted
- All customer-facing text is jargon-free and action-oriented
- Every agent thought and action is logged to `logs/agent_trace.json`

## Supported Error Codes

| Code | Description | Auto-fixable |
|---|---|---|
| 402 | Invalid zip code | ✅ Yes |
| 415 | Missing / malformed date of birth | ✅ Yes |
| 610 | SSN format error | ✅ Yes |
| 501 | Duplicate enrollment | ❌ Human review |
| 308 | Invalid plan code | ❌ Human review |

## Tech Stack

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — stateful agent DAG
- **[FastAPI](https://fastapi.tiangolo.com/)** — REST API + static file serving
- **Vanilla HTML/CSS/JS** — zero-dependency frontend
