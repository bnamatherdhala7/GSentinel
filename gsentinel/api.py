import json
import sys
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

sys.path.insert(0, str(Path(__file__).parent))

from graph.state import FulfillmentState
from graph.nodes import parser_node, healer_node, critic_node, messenger_node

app = FastAPI(title="GSentinel API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE = Path(__file__).parent


def run_pipeline_with_timing():
    raw = (BASE / "mocks/carrier_logs/sample_error.txt").read_text()
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
    }

    steps = []

    t0 = time.time()
    state = parser_node(state)
    steps.append({
        "node": "parser",
        "label": "Parser",
        "duration_ms": round((time.time() - t0) * 1000),
        "inputs": {"raw_input": state["raw_input"][:120] + "..."},
        "outputs": {
            "employee_id": state["employee_id"],
            "error_code": state["error_code"],
            "field_affected": state["field_affected"],
            "submitted_value": state["submitted_value"],
            "error_description": state["error_description"],
        },
        "trace": state["trace"][-1],
    })

    t1 = time.time()
    state = healer_node(state)
    steps.append({
        "node": "healer",
        "label": "Healer",
        "duration_ms": round((time.time() - t1) * 1000),
        "inputs": {
            "employee_id": state["employee_id"],
            "error_code": state["error_code"],
        },
        "outputs": {
            "corrected_value": state["corrected_value"],
            "source": "internal_db.json",
        },
        "trace": state["trace"][-1],
    })

    t2 = time.time()
    state = critic_node(state)
    steps.append({
        "node": "critic",
        "label": "Critic",
        "duration_ms": round((time.time() - t2) * 1000),
        "inputs": {"corrected_value": state["corrected_value"]},
        "outputs": {
            "confidence_score": state["confidence_score"],
            "valid": state["confidence_score"] >= 0.9,
        },
        "trace": state["trace"][-1],
    })

    t3 = time.time()
    state = messenger_node(state)
    steps.append({
        "node": "messenger",
        "label": "Messenger",
        "duration_ms": round((time.time() - t3) * 1000),
        "inputs": {"confidence_score": state["confidence_score"]},
        "outputs": {
            "status": state["status"],
            "action_card": state["action_card"],
        },
        "trace": state["trace"][-1],
    })

    log_path = BASE / "logs/agent_trace.json"
    log_path.write_text(json.dumps(state["trace"], indent=2))

    return {
        "steps": steps,
        "action_card": state["action_card"],
        "status": state["status"],
        "confidence_score": state["confidence_score"],
        "total_ms": round((time.time() - t0) * 1000),
        "employee_id": state["employee_id"],
        "error_code": state["error_code"],
        "submitted_value": state["submitted_value"],
        "corrected_value": state["corrected_value"],
    }


@app.get("/api/run")
def run_agent():
    return run_pipeline_with_timing()


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
