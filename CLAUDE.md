You are building GSentinel, an Agentic Benefits Fulfillment Engine. Read every instruction below carefully and execute them in order without stopping. Do not ask clarifying questions — make reasonable decisions and keep building.

HARD RULES (never violate these):

No external no-code tools (no n8n, Zapier, Make)
Never mention "Gusto" or any third-party brand in UI, code, or logs
Never let the LLM guess a premium, SSN, or financial field — use code-based lookups only
Every auto-fix must pass SchemaValidator before submission
Log every agent thought and action to logs/agent_trace.json
All customer-facing text must be jargon-free and action-oriented


STEP 1 — SCAFFOLD THE FILE STRUCTURE
Create this exact directory and file tree:
gsentinel/
├── CLAUDE.md
├── sentinel.py
├── graph/
│   ├── __init__.py
│   ├── state.py
│   └── nodes.py
├── data/
│   ├── internal_db.json
│   └── knowledge/
│       └── carrier_errors.md
├── schema/
│   └── standard_enr.json
├── mocks/
│   └── carrier_logs/
│       └── sample_error.txt
└── logs/
    └── agent_trace.json

STEP 2 — CREATE MOCK DATA
data/internal_db.json — 3 employee records. Employee #2 (Jordan Smith) must have a 4-digit zip code (intentional typo — should be 5 digits):
json{
  "employees": [
    {
      "id": "EMP001",
      "name": "Alex Rivera",
      "dob": "1988-03-14",
      "ssn_last4": "4821",
      "address": {
        "street": "412 Maple Ave",
        "city": "Austin",
        "state": "TX",
        "zip": "78701"
      },
      "plan": "GOLD_PPO",
      "dependents": []
    },
    {
      "id": "EMP002",
      "name": "Jordan Smith",
      "dob": "1992-07-22",
      "ssn_last4": "3367",
      "address": {
        "street": "89 Birch Lane",
        "city": "Denver",
        "state": "CO",
        "zip": "8020"
      },
      "plan": "SILVER_HMO",
      "dependents": [
        { "name": "Casey Smith", "dob": "2019-11-05", "relation": "child" }
      ]
    },
    {
      "id": "EMP003",
      "name": "Morgan Lee",
      "dob": "1979-01-30",
      "ssn_last4": "9104",
      "address": {
        "street": "210 Oak Street",
        "city": "Portland",
        "state": "OR",
        "zip": "97201"
      },
      "plan": "BRONZE_EPO",
      "dependents": []
    }
  ]
}
data/knowledge/carrier_errors.md — carrier error code reference:
markdown# Carrier Error Code Reference

## Error 402 — Invalid Zip Code
The zip code submitted does not match USPS 5-digit format. Cross-reference internal HR record and resubmit with corrected zip.

## Error 415 — Missing Date of Birth
A required date of birth field is blank or malformed. Must be formatted YYYY-MM-DD. Required for all dependents.

## Error 501 — Duplicate Enrollment
This employee ID was already submitted in the current enrollment window. Check for duplicate records before resubmitting.

## Error 308 — Invalid Plan Code
The plan code submitted does not match any active carrier plan for this group. Verify plan codes against the current carrier contract.

## Error 610 — SSN Format Error
The Social Security Number field is malformed or contains non-numeric characters. SSN last 4 must be exactly 4 digits.
mocks/carrier_logs/sample_error.txt — raw carrier rejection for Jordan Smith:
CARRIER REJECTION NOTICE
Date: 2026-04-19
Group ID: GRP-00142
---
RECORD: EMP002 | Jordan Smith
ERROR CODE: 402
FIELD: address.zip
SUBMITTED VALUE: "8020"
MESSAGE: Zip code must be exactly 5 digits. Enrollment rejected pending correction.
---
END OF REJECTION NOTICE
schema/standard_enr.json — gold standard enrollment schema:
json{
  "required_fields": ["id", "name", "dob", "ssn_last4", "address", "plan"],
  "address_required": ["street", "city", "state", "zip"],
  "zip_format": "^[0-9]{5}$",
  "dob_format": "YYYY-MM-DD",
  "ssn_last4_format": "^[0-9]{4}$",
  "valid_plans": ["GOLD_PPO", "SILVER_HMO", "BRONZE_EPO", "PLATINUM_PPO"]
}

STEP 3 — BUILD graph/state.py
Define a FulfillmentState TypedDict with these exact fields:
pythonfrom typing import TypedDict, Optional
from enum import Enum

class FulfillmentStatus(str, Enum):
    AUTO_FIXED = "AUTO_FIXED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    NOTIFIED = "NOTIFIED"

class FulfillmentState(TypedDict):
    raw_input: str                  # Raw carrier rejection text
    employee_id: Optional[str]      # Extracted employee ID
    error_code: Optional[str]       # Extracted error code (e.g. "402")
    error_description: Optional[str] # Human-readable from knowledge base
    field_affected: Optional[str]   # Which field caused the rejection
    submitted_value: Optional[str]  # What the carrier received
    corrected_value: Optional[str]  # What the Healer proposes
    confidence_score: float         # 0.0 to 1.0
    action_card: Optional[str]      # Final customer-facing message
    status: Optional[FulfillmentStatus]
    trace: list                     # Append agent logs here

STEP 4 — BUILD graph/nodes.py
Build four node functions. Each must append a trace entry to state["trace"] before returning.
parser_node(state)

Parse state["raw_input"] using regex or string matching to extract: employee ID, error code, field affected, submitted value
Open data/knowledge/carrier_errors.md and find the matching error code section
Set state["error_description"] to the plain-English explanation from the knowledge file
Return updated state

healer_node(state)

Load data/internal_db.json
Look up the employee by state["employee_id"]
Based on state["error_code"], apply the correct fix using only data from the DB (no LLM guessing):

Error 402: Pull the correct zip from the DB record
Error 415: Pull the correct DOB from the DB record
Error 610: Pull the correct ssn_last4 from the DB record


Set state["corrected_value"] to the DB value
Return updated state

critic_node(state)

Load schema/standard_enr.json
Validate state["corrected_value"] against the schema rule for the affected field (use regex)
If valid: set confidence_score = 0.95
If invalid or uncertain: set confidence_score = 0.5
Return updated state

messenger_node(state)

If confidence_score >= 0.9: write a success action card and set status = AUTO_FIXED
If confidence_score < 0.9: write a human-review action card and set status = HUMAN_REVIEW
Action card format (jargon-free, action-oriented):

Success: "✅ Fixed automatically: We corrected a zip code typo in Jordan Smith's enrollment (8020 → 80201). No action needed."
Review: "⚠️ Action needed: We couldn't auto-correct [field] for [name]. Please review and update their record."


Return updated state


STEP 5 — BUILD sentinel.py
Wire the full LangGraph DAG:
parser_node → healer_node → critic_node → [conditional] → messenger_node
Conditional edge logic:

If confidence_score >= 0.9 → route to messenger_node with AUTO_FIXED path
If confidence_score < 0.9 → route to messenger_node with HUMAN_REVIEW path

Entry point:

Read mocks/carrier_logs/sample_error.txt as the initial raw_input
Run the graph
Print the final action_card to console
Write the full state["trace"] to logs/agent_trace.json with indent=2


STEP 6 — VERIFY
Run sentinel.py. Confirm:

The console prints a clean, jargon-free action card
logs/agent_trace.json contains a trace entry from each of the 4 nodes
The corrected zip code (80201) was sourced from internal_db.json, not generated by the LLM
No errors or exceptions

If any step fails, debug and fix before stopping.

Build the complete working system now.

---

STEP 7 — VISUAL FRONTEND (COMPLETED)

A web UI has been added to visualize the full agentic pipeline.

New files:
gsentinel/
├── api.py              # FastAPI server — serves REST API + static frontend
└── frontend/
    └── index.html      # Single-page visual workflow app

To start the server:
  cd gsentinel
  uvicorn api.py:app --reload --port 8000

Then open: http://localhost:8000

Features:
- Live pipeline visualization: 4 animated nodes (Parser → Healer → Critic → Messenger)
- Each node shows inputs/outputs/timing on click
- Confidence meter, action card, correction summary
- Full agent trace log in the UI
- Dark-mode, no external dependencies

HARD RULES ADDITIONS:
- Frontend must never display raw SSN, only ssn_last4 where shown
- No third-party analytics or tracking scripts in the frontend
