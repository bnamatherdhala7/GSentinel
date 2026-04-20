import re
import json
from pathlib import Path

BASE = Path(__file__).parent.parent


def parser_node(state: dict) -> dict:
    text = state["raw_input"]

    emp_match = re.search(r"RECORD:\s*(EMP\d+)", text)
    err_match = re.search(r"ERROR CODE:\s*(\d+)", text)
    field_match = re.search(r"FIELD:\s*(\S+)", text)
    val_match = re.search(r'SUBMITTED VALUE:\s*"([^"]*)"', text)

    state["employee_id"] = emp_match.group(1) if emp_match else None
    state["error_code"] = err_match.group(1) if err_match else None
    state["field_affected"] = field_match.group(1) if field_match else None
    state["submitted_value"] = val_match.group(1) if val_match else None

    kb = (BASE / "data/knowledge/carrier_errors.md").read_text()
    code = state["error_code"]
    section = re.search(rf"## Error {code}[^\n]*\n(.*?)(?=\n## |\Z)", kb, re.DOTALL)
    state["error_description"] = section.group(1).strip() if section else f"Unknown error {code}"

    state["trace"].append({
        "node": "parser",
        "employee_id": state["employee_id"],
        "error_code": state["error_code"],
        "field_affected": state["field_affected"],
        "submitted_value": state["submitted_value"],
        "error_description": state["error_description"],
    })
    return state


def healer_node(state: dict) -> dict:
    db = json.loads((BASE / "data/internal_db.json").read_text())
    emp = next((e for e in db["employees"] if e["id"] == state["employee_id"]), None)

    corrected = None
    if emp:
        code = state["error_code"]
        if code == "402":
            corrected = emp["address"]["zip"]
        elif code == "415":
            corrected = emp["dob"]
        elif code == "610":
            corrected = emp["ssn_last4"]

    state["corrected_value"] = corrected
    state["trace"].append({
        "node": "healer",
        "employee_id": state["employee_id"],
        "error_code": state["error_code"],
        "corrected_value": corrected,
        "source": "internal_db.json",
    })
    return state


def critic_node(state: dict) -> dict:
    schema = json.loads((BASE / "schema/standard_enr.json").read_text())
    code = state["error_code"]
    value = state["corrected_value"] or ""

    pattern_map = {
        "402": schema["zip_format"],
        "415": r"^\d{4}-\d{2}-\d{2}$",
        "610": schema["ssn_last4_format"],
    }

    pattern = pattern_map.get(code)
    valid = bool(pattern and re.match(pattern, value))
    state["confidence_score"] = 0.95 if valid else 0.5

    state["trace"].append({
        "node": "critic",
        "corrected_value": value,
        "pattern": pattern,
        "valid": valid,
        "confidence_score": state["confidence_score"],
    })
    return state


def messenger_node(state: dict) -> dict:
    emp_id = state["employee_id"]
    field = state["field_affected"]
    original = state["submitted_value"]
    corrected = state["corrected_value"]
    score = state["confidence_score"]

    db = json.loads((BASE / "data/internal_db.json").read_text())
    emp = next((e for e in db["employees"] if e["id"] == emp_id), None)
    name = emp["name"] if emp else emp_id

    if score >= 0.9:
        state["action_card"] = (
            f"✅ Fixed automatically: We corrected a zip code typo in {name}'s "
            f"enrollment ({original} → {corrected}). No action needed."
        )
        state["status"] = "AUTO_FIXED"
    else:
        state["action_card"] = (
            f"⚠️ Action needed: We couldn't auto-correct {field} for {name}. "
            "Please review and update their record."
        )
        state["status"] = "HUMAN_REVIEW"

    state["trace"].append({
        "node": "messenger",
        "status": state["status"],
        "action_card": state["action_card"],
    })
    return state
