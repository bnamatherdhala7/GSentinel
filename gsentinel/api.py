import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from graph.state import FulfillmentState
from graph.nodes import parser_node, healer_node, critic_node, messenger_node

app = FastAPI(title="GSentinel API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE = Path(__file__).parent

MOCK_QUEUE = [
    {
        "id": "REJ-001", "employee_id": "EMP002", "employee_name": "Jordan Smith",
        "error_code": "402", "field": "address.zip", "status": "AUTO_FIXED",
        "scenario_file": "scenario_402.txt", "timestamp": "2026-04-20T08:14:00Z",
    },
    {
        "id": "REJ-002", "employee_id": "EMP002", "employee_name": "Jordan Smith",
        "error_code": "415", "field": "dependents[1].dob", "status": "HUMAN_REVIEW",
        "scenario_file": "scenario_415.txt", "timestamp": "2026-04-20T08:31:00Z",
    },
    {
        "id": "REJ-003", "employee_id": "EMP003", "employee_name": "Morgan Lee",
        "error_code": "501", "field": "enrollment_id", "status": "HUMAN_REVIEW",
        "scenario_file": "scenario_501.txt", "timestamp": "2026-04-20T09:02:00Z",
    },
    {
        "id": "REJ-004", "employee_id": "EMP001", "employee_name": "Alex Rivera",
        "error_code": "402", "field": "address.zip", "status": "AUTO_FIXED",
        "scenario_file": "scenario_402.txt", "timestamp": "2026-04-20T09:45:00Z",
    },
    {
        "id": "REJ-005", "employee_id": "EMP003", "employee_name": "Morgan Lee",
        "error_code": "610", "field": "ssn_last4", "status": "PENDING",
        "scenario_file": None, "timestamp": "2026-04-20T10:12:00Z",
    },
    {
        "id": "REJ-006", "employee_id": "EMP001", "employee_name": "Alex Rivera",
        "error_code": "308", "field": "plan_code", "status": "PENDING",
        "scenario_file": None, "timestamp": "2026-04-20T10:58:00Z",
    },
]


class RunRequest(BaseModel):
    scenario_file: Optional[str] = None


class ResolveRequest(BaseModel):
    rejection_id: str
    action: str  # "confirm" | "override" | "escalate"
    override_value: Optional[str] = None


def run_pipeline_with_timing(scenario_file: Optional[str] = None):
    if scenario_file:
        file_path = BASE / f"mocks/carrier_logs/{scenario_file}"
    else:
        file_path = BASE / "mocks/carrier_logs/sample_error.txt"
    raw = file_path.read_text()

    state: FulfillmentState = {
        "raw_input": raw,
        "employee_id": None,
        "error_code": None,
        "error_description": None,
        "field_affected": None,
        "submitted_value": None,
        "corrected_value": None,
        "confidence_score": 0.0,
        "action_card": None,
        "status": None,
        "trace": [],
        "latency_ms": {},
        "kb_evidence": "",
        "reasoning_path": [],
    }

    steps = []
    t0 = time.time()

    state = parser_node(state)
    pt = state["trace"][-1]
    steps.append({
        "node": "parser", "label": "Parser",
        "duration_ms": pt["latency_ms"],
        "inputs": {"raw_input": raw[:120] + "..."},
        "outputs": {
            "employee_id": state["employee_id"],
            "error_code": state["error_code"],
            "field_affected": state["field_affected"],
            "submitted_value": state["submitted_value"],
            "error_description": state["error_description"],
            "top_candidates": pt["top_candidates"],
            "kb_evidence_chars": pt["kb_evidence_chars"],
        },
        "reasoning": pt["reasoning"],
        "trace": pt,
    })

    state = healer_node(state)
    ht = state["trace"][-1]
    steps.append({
        "node": "healer", "label": "Healer",
        "duration_ms": ht["latency_ms"],
        "inputs": {"employee_id": state["employee_id"], "error_code": state["error_code"]},
        "outputs": {
            "corrected_value": state["corrected_value"],
            "match_index": ht["match_index"],
            "mismatch_log": ht["mismatch_log"],
            "search_depth": ht["search_depth"],
            "source": "internal_db.json",
        },
        "reasoning": state["reasoning_path"][-1] if state["reasoning_path"] else "",
        "trace": ht,
    })

    state = critic_node(state)
    ct = state["trace"][-1]
    steps.append({
        "node": "critic", "label": "Critic",
        "duration_ms": ct["latency_ms"],
        "inputs": {
            "corrected_value": state["corrected_value"],
            "pattern_tested": ct["pattern_tested"],
        },
        "outputs": {
            "confidence_score": state["confidence_score"],
            "valid": state["confidence_score"] >= 0.9,
            "checks_passed": ct["checks_passed"],
            "checks_total": ct["checks_total"],
            "validation_log": ct["validation_log"],
            "summary": ct["summary"],
        },
        "reasoning": state["reasoning_path"][-1] if state["reasoning_path"] else "",
        "trace": ct,
    })

    state = messenger_node(state)
    mt = state["trace"][-1]
    steps.append({
        "node": "messenger", "label": "Messenger",
        "duration_ms": mt["latency_ms"],
        "inputs": {"confidence_score": state["confidence_score"]},
        "outputs": {"status": state["status"], "action_card": state["action_card"]},
        "reasoning": state["reasoning_path"][-1] if state["reasoning_path"] else "",
        "trace": mt,
    })

    log_path = BASE / "logs/agent_trace.json"
    log_path.write_text(json.dumps(state["trace"], indent=2))

    critic_t = next(t for t in state["trace"] if t["node"] == "critic")
    healer_t = next(t for t in state["trace"] if t["node"] == "healer")

    return {
        "steps": steps,
        "action_card": state["action_card"],
        "status": state["status"],
        "confidence_score": state["confidence_score"],
        "total_ms": round((time.time() - t0) * 1000),
        "employee_id": state["employee_id"],
        "error_code": state["error_code"],
        "field_affected": state["field_affected"],
        "submitted_value": state["submitted_value"],
        "corrected_value": state["corrected_value"],
        "error_description": state["error_description"],
        "compliance_report": {
            "latency_ms": state["latency_ms"],
            "total_ms": sum(state["latency_ms"].values()),
            "db_records_scanned": len(healer_t.get("search_depth", [])),
            "mismatch_log": healer_t.get("mismatch_log"),
            "checks_passed": critic_t.get("checks_passed"),
            "checks_total": critic_t.get("checks_total"),
            "validation_log": critic_t.get("validation_log", []),
            "kb_evidence": state["kb_evidence"],
            "kb_evidence_chars": len(state["kb_evidence"]),
            "reasoning_path": state["reasoning_path"],
        },
        "reasoning_path": state["reasoning_path"],
        "kb_evidence": state["kb_evidence"],
    }


@app.post("/api/run")
def run_agent(request: RunRequest = None):
    scenario = request.scenario_file if request else None
    return run_pipeline_with_timing(scenario_file=scenario)


@app.get("/api/queue")
def get_queue():
    return MOCK_QUEUE


@app.post("/api/resolve")
def resolve_rejection(request: ResolveRequest):
    ts = datetime.now(timezone.utc).isoformat()
    resolution = {
        "node": "human_resolver",
        "rejection_id": request.rejection_id,
        "resolved_by": "human",
        "action": request.action,
        "override_value": request.override_value,
        "timestamp": ts,
    }
    log_path = BASE / "logs/agent_trace.json"
    try:
        existing = json.loads(log_path.read_text()) if log_path.exists() else []
    except Exception:
        existing = []
    existing.append(resolution)
    log_path.write_text(json.dumps(existing, indent=2))
    return {"rejection_id": request.rejection_id, "resolved_by": "human",
            "action": request.action, "timestamp": ts}


@app.get("/api/trace")
def get_trace():
    log_path = BASE / "logs/agent_trace.json"
    if log_path.exists():
        return json.loads(log_path.read_text())
    return []


@app.get("/api/raw-input")
def get_raw_input():
    return {"text": (BASE / "mocks/carrier_logs/sample_error.txt").read_text()}


@app.get("/api/db")
def get_db():
    return json.loads((BASE / "data/internal_db.json").read_text())


app.mount("/", StaticFiles(directory=str(BASE / "frontend"), html=True), name="frontend")
