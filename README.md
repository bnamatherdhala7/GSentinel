# GSentinel

**`LangGraph`** · **`FastAPI`** · **`4 Agents`** · **`No LLM guessing on financial fields`** · **`Vanilla HTML/JS`**

Benefits enrollment rejections sit in a queue for days while HR teams manually cross-reference carrier notices against employee records. GSentinel reads a raw carrier rejection, diagnoses the root cause, pulls the authoritative value from your HR database, validates the fix against the enrollment schema, and either resolves it automatically or routes it to a human — in a single pipeline run.

---

## The Problem in One Line

A mis-typed zip code can delay an employee's insurance coverage by weeks. The carrier sends a rejection notice. Someone has to read it, find the right employee record, verify the correct value, and resubmit. GSentinel does all of that automatically.

---

## How It Works

1. **You feed it a carrier rejection** — raw text from the carrier's rejection notice
2. **Four agents run in sequence** — Parser extracts the facts → Healer looks up the correct value → Critic validates against the enrollment schema → Messenger generates the action card
3. **One of two outcomes appears** — `AUTO_FIXED` (confidence ≥ 90%) or `HUMAN_REVIEW` (routed for manual correction)
4. **Every decision is logged** — full agent trace written to `logs/agent_trace.json` after every run

---

## The 4 Agents

| Agent | Role | Input → Output |
|-------|------|----------------|
| 🔍 **Parser** | Extracts employee ID, error code, field, and submitted value from the rejection text. Looks up the plain-English error description from the knowledge base. | Raw rejection text → `{ employee_id, error_code, field_affected, submitted_value, error_description }` |
| 🩺 **Healer** | Looks up the correct value from the internal HR database. Never guesses — code-only lookups. | `{ employee_id, error_code }` → `{ corrected_value }` |
| ⚖️ **Critic** | Validates the corrected value against the enrollment schema using regex. Sets a confidence score. | `{ corrected_value }` → `{ confidence_score: 0.95 \| 0.5 }` |
| 📨 **Messenger** | Generates a jargon-free action card and sets the fulfillment status. | `{ confidence_score }` → `{ action_card, status: AUTO_FIXED \| HUMAN_REVIEW }` |

---

## Example

**Input** — carrier rejection for EMP002:
```
CARRIER REJECTION NOTICE
Date: 2026-04-19
RECORD: EMP002 | Jordan Smith
ERROR CODE: 402
FIELD: address.zip
SUBMITTED VALUE: "8020"
MESSAGE: Zip code must be exactly 5 digits.
```

**Output** — action card:
```
✅ Fixed automatically: We corrected a zip code typo in Jordan Smith's
   enrollment (8020 → 80201). No action needed.
```

---

## Architecture

```
Carrier Rejection Notice (raw text)
            │
            ▼
    ┌───────────────┐
    │    Parser     │  Regex extraction + knowledge base lookup
    └───────┬───────┘
            │  { employee_id, error_code, field_affected }
            ▼
    ┌───────────────┐
    │    Healer     │  Internal DB lookup only — no LLM guessing
    └───────┬───────┘
            │  { corrected_value }
            ▼
    ┌───────────────┐
    │    Critic     │  Schema regex validation → confidence score
    └───────┬───────┘
            │
       ┌────┴─────┐
    ≥ 0.9       < 0.9
       │           │
  AUTO_FIX    HUMAN_REVIEW
       │           │
       └─────┬─────┘
             ▼
    ┌───────────────┐
    │   Messenger   │  Jargon-free action card
    └───────────────┘
            │
            ▼
    logs/agent_trace.json
```

Every node appends a structured entry to `logs/agent_trace.json` — full reasoning chain, always auditable.

---

## Supported Error Codes

| Code | Issue | Auto-fixable | DB field used |
|------|-------|:------------:|---------------|
| 402 | Invalid zip code | ✅ | `address.zip` |
| 415 | Missing / malformed date of birth | ✅ | `dob` |
| 610 | SSN format error | ✅ | `ssn_last4` |
| 501 | Duplicate enrollment | ❌ | — |
| 308 | Invalid plan code | ❌ | — |

---

## Quickstart

**Prerequisites:**
```bash
pip install langgraph fastapi uvicorn
```

**Run the CLI pipeline:**
```bash
cd gsentinel
python sentinel.py
```

**Run the visual web UI:**
```bash
cd gsentinel
uvicorn api:app --reload --port 8000
```

Open **http://localhost:8000** — watch each agent node animate in real time, click any node to inspect its inputs and outputs, and see the final action card.

---

## Project Structure

```
GSentinel/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CLAUDE.md                         # Build spec & hard rules
├── .gitignore
└── gsentinel/
    ├── sentinel.py                   # LangGraph DAG — CLI entry point
    ├── api.py                        # FastAPI server + static frontend host
    ├── graph/
    │   ├── state.py                  # FulfillmentState TypedDict
    │   └── nodes.py                  # Parser, Healer, Critic, Messenger
    ├── data/
    │   ├── internal_db.json          # Employee HR records (source of truth)
    │   └── knowledge/
    │       └── carrier_errors.md     # Error code plain-English reference
    ├── schema/
    │   └── standard_enr.json         # Enrollment validation schema
    ├── mocks/
    │   └── carrier_logs/
    │       └── sample_error.txt      # Sample carrier rejection (EMP002, Error 402)
    ├── frontend/
    │   └── index.html                # Single-page visual pipeline UI
    └── logs/
        └── agent_trace.json          # Runtime output — not committed
```

---

## Web UI

The visual interface (`http://localhost:8000`) shows the full pipeline in real time:

- **Animated node pipeline** — each node pulses blue while running, turns green when done
- **Per-node inspection** — click any node to see its exact inputs, outputs, and processing time
- **Confidence meter** — live bar showing 0–100% validation score
- **Correction summary** — submitted value vs. corrected value side by side
- **Agent trace log** — every trace entry from `logs/agent_trace.json` rendered in the browser

---

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Agent orchestration | LangGraph | Stateful DAG with conditional routing between nodes |
| API server | FastAPI | REST endpoints + static file serving in one process |
| Frontend | Vanilla HTML + CSS + JS | Zero build step, zero dependencies |
| Validation | Python `re` (regex) | Schema rules defined in `standard_enr.json`, never LLM |
| Data source | `internal_db.json` | Authoritative HR record — Healer never guesses |

---

## Docs

- [`docs/prd.md`](docs/prd.md) — Product Requirements Document: business problem, market analysis, competitive landscape, OKRs, release plan
- [`CLAUDE.md`](CLAUDE.md) — Build spec: hard rules, node contracts, pipeline definition
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Branching strategy, commit format, PR process
- [`CHANGELOG.md`](CHANGELOG.md) — Versioned change history
- [`gsentinel/data/knowledge/carrier_errors.md`](gsentinel/data/knowledge/carrier_errors.md) — Carrier error code reference used by Parser

---

## Out of Scope (v1)

- Real carrier API submission (mock pipeline only)
- Multi-rejection batch processing
- User authentication or multi-tenant support
- Email / Slack notification delivery
- LLM-assisted correction for unstructured errors

---

*Built to eliminate the gap between a carrier rejection notice and a corrected enrollment.*
