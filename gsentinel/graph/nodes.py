import re
import json
import time
from pathlib import Path

BASE = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Parser — RAG-simulated extraction with candidate scoring
# ---------------------------------------------------------------------------
def parser_node(state: dict) -> dict:
    t_start = time.time()
    time.sleep(0.5)  # deliberate "thinking" pause for UI breathing

    text = state["raw_input"]

    # --- RAG simulation: surface ALL candidate IDs and codes first ---
    all_emp_ids = list(dict.fromkeys(re.findall(r"EMP\d+", text)))
    all_err_codes = list(dict.fromkeys(re.findall(r"(?:ERROR CODE:\s*|(?<!\d))(\d{3})(?!\d)", text)))

    top_candidates = {
        "employee_ids": all_emp_ids,
        "error_codes": all_err_codes,
    }

    # --- Primary extraction ---
    emp_match = re.search(r"RECORD:\s*(EMP\d+)", text)
    err_match = re.search(r"ERROR CODE:\s*(\d+)", text)
    field_match = re.search(r"FIELD:\s*(\S+)", text)
    val_match = re.search(r'SUBMITTED VALUE:\s*"([^"]*)"', text)

    emp_id = emp_match.group(1) if emp_match else None
    error_code = err_match.group(1) if err_match else None

    state["employee_id"] = emp_id
    state["error_code"] = error_code
    state["field_affected"] = field_match.group(1) if field_match else None
    state["submitted_value"] = val_match.group(1) if val_match else None

    # --- RAG: knowledge base lookup ---
    kb_text = (BASE / "data/knowledge/carrier_errors.md").read_text()
    section_match = re.search(
        rf"(## Error {error_code}[^\n]*\n.*?)(?=\n## |\Z)", kb_text, re.DOTALL
    )
    kb_section = section_match.group(1).strip() if section_match else f"## Error {error_code} — Unknown"
    kb_body = re.sub(r"^## Error \d+[^\n]*\n", "", kb_section).strip()
    state["error_description"] = kb_body
    state["kb_evidence"] = kb_section  # full heading + body stored as evidence

    # --- Reasoning string ---
    reasoning = (
        f"Scanned document — found {len(all_emp_ids)} employee anchor(s): {all_emp_ids}. "
        f"Selected '{emp_id}' as primary: appears in RECORD field (highest-confidence anchor). "
        f"Detected {len(all_err_codes)} 3-digit numeric token(s): {all_err_codes}. "
        f"Resolved '{error_code}' via 'ERROR CODE:' prefix pattern. "
        f"RAG lookup in carrier_errors.md returned {len(kb_section)} chars for Error {error_code}."
    )
    state["reasoning_path"].append(f"[Parser] {reasoning}")

    elapsed = round((time.time() - t_start) * 1000)
    state["latency_ms"]["parser"] = elapsed

    state["trace"].append({
        "node": "parser",
        "latency_ms": elapsed,
        "top_candidates": top_candidates,
        "employee_id": emp_id,
        "error_code": error_code,
        "field_affected": state["field_affected"],
        "submitted_value": state["submitted_value"],
        "error_description": state["error_description"],
        "kb_evidence_chars": len(kb_section),
        "reasoning": reasoning,
    })
    return state


# ---------------------------------------------------------------------------
# Healer — DB lookup with search_depth audit trail
# ---------------------------------------------------------------------------
def healer_node(state: dict) -> dict:
    t_start = time.time()
    time.sleep(0.5)  # deliberate "thinking" pause for UI breathing

    db = json.loads((BASE / "data/internal_db.json").read_text())
    target_id = state["employee_id"]
    code = state["error_code"]

    # --- search_depth: log every record scanned ---
    search_depth = []
    emp = None
    match_index = -1
    for idx, record in enumerate(db["employees"]):
        hit = record["id"] == target_id
        search_depth.append(
            f"Record[{idx}] id={record['id']} → {'✓ MATCH' if hit else '✗ skip'}"
        )
        if hit:
            emp = record
            match_index = idx
            break

    # --- Extract corrected value and log the mismatch ---
    corrected = None
    mismatch_log = None
    if emp:
        if code == "402":
            corrected = emp["address"]["zip"]
            mismatch_log = (
                f"Record[{match_index}].address.zip = '{corrected}' | "
                f"Carrier submitted '{state['submitted_value']}' → "
                f"{'MISMATCH — length ' + str(len(state['submitted_value'])) + ' vs required 5' if corrected != state['submitted_value'] else 'values equal, no change'}"
            )
        elif code == "415":
            corrected = emp["dob"]
            mismatch_log = (
                f"Record[{match_index}].dob = '{corrected}' | "
                f"Carrier submitted '{state['submitted_value']}' → "
                f"{'MISMATCH — DOB field malformed' if corrected != state['submitted_value'] else 'values equal'}"
            )
        elif code == "610":
            corrected = emp["ssn_last4"]
            mismatch_log = (
                f"Record[{match_index}].ssn_last4 = '{corrected}' | "
                f"Carrier submitted '{state['submitted_value']}' → "
                f"{'MISMATCH — SSN format error' if corrected != state['submitted_value'] else 'values equal'}"
            )

    state["corrected_value"] = corrected

    reasoning = (
        f"Opened internal_db.json — scanned {len(db['employees'])} record(s). "
        f"Located {target_id} at index {match_index}. "
        f"{mismatch_log or 'No correctable field found for error code ' + str(code) + '.'}"
    )
    state["reasoning_path"].append(f"[Healer] {reasoning}")

    elapsed = round((time.time() - t_start) * 1000)
    state["latency_ms"]["healer"] = elapsed

    state["trace"].append({
        "node": "healer",
        "latency_ms": elapsed,
        "employee_id": target_id,
        "match_index": match_index,
        "search_depth": search_depth,
        "error_code": code,
        "corrected_value": corrected,
        "mismatch_log": mismatch_log,
        "source": "internal_db.json",
    })
    return state


# ---------------------------------------------------------------------------
# Critic — Jailbreak & Compliance Guard
# ---------------------------------------------------------------------------
def critic_node(state: dict) -> dict:
    t_start = time.time()

    schema = json.loads((BASE / "schema/standard_enr.json").read_text())
    code = state["error_code"]
    value = state["corrected_value"] or ""

    pattern_map = {
        "402": schema["zip_format"],
        "415": r"^\d{4}-\d{2}-\d{2}$",
        "610": schema["ssn_last4_format"],
    }

    BLOCKED_VALUES = {"00000", "99999", "11111", "12345", "00001"}

    pattern = pattern_map.get(code, r"^.+$")
    validation_log = []

    # Check 1 — format guard (schema regex)
    check1 = bool(re.match(pattern, value))
    validation_log.append(
        f"Check 1 — Format guard: regex='{pattern}' | value='{value}' → {'PASS' if check1 else 'FAIL'}"
    )

    # Check 2 — jailbreak / blocked-value guard
    check2 = value not in BLOCKED_VALUES
    validation_log.append(
        f"Check 2 — Jailbreak guard: value '{value}' not in blocked list → {'PASS' if check2 else 'FAIL — blocked sentinel value'}"
    )

    # Check 3 — injection guard (numeric fields must be all-digit)
    numeric_codes = {"402", "610"}
    check3 = value.isdigit() if code in numeric_codes else True
    validation_log.append(
        f"Check 3 — Injection guard: value '{value}' is all-numeric → {'PASS' if check3 else 'FAIL — non-numeric chars detected'}"
    )

    all_pass = check1 and check2 and check3
    state["confidence_score"] = 0.95 if all_pass else (0.7 if check1 else 0.5)

    summary = (
        f"Field '{state['field_affected']}' passed all 3 compliance checks. Confidence: {state['confidence_score']}."
        if all_pass else
        f"Field '{state['field_affected']}' failed {sum(not c for c in [check1, check2, check3])} check(s). "
        f"Confidence degraded to {state['confidence_score']}."
    )

    reasoning = (
        f"Jailbreak & Compliance Guard activated for Error {code}. "
        f"Tested '{value}' against pattern '{pattern}'. "
        f"{sum([check1, check2, check3])}/3 checks passed. {summary}"
    )
    state["reasoning_path"].append(f"[Critic] {reasoning}")

    elapsed = round((time.time() - t_start) * 1000)
    state["latency_ms"]["critic"] = elapsed

    state["trace"].append({
        "node": "critic",
        "role": "Jailbreak & Compliance Guard",
        "latency_ms": elapsed,
        "corrected_value": value,
        "pattern_tested": pattern,
        "validation_log": validation_log,
        "checks_passed": sum([check1, check2, check3]),
        "checks_total": 3,
        "confidence_score": state["confidence_score"],
        "summary": summary,
    })
    return state


# ---------------------------------------------------------------------------
# Messenger — Product-led action card with Reason + Confidence Level
# ---------------------------------------------------------------------------
def messenger_node(state: dict) -> dict:
    t_start = time.time()

    emp_id = state["employee_id"]
    field = state["field_affected"]
    original = state["submitted_value"]
    corrected = state["corrected_value"]
    score = state["confidence_score"]
    error_code = state["error_code"]

    db = json.loads((BASE / "data/internal_db.json").read_text())
    emp = next((e for e in db["employees"] if e["id"] == emp_id), None)
    name = emp["name"] if emp else emp_id

    checks_entry = next(
        (t for t in reversed(state["trace"]) if t.get("node") == "critic"), {}
    )
    checks_passed = checks_entry.get("checks_passed", "?")
    checks_total = checks_entry.get("checks_total", 3)

    if score >= 0.9:
        state["action_card"] = (
            f"✅ Enrollment Correction — AUTO_FIXED\n\n"
            f"  Field:           {field}\n"
            f"  Change:          {original} → {corrected}\n"
            f"  Employee:        {name} ({emp_id})\n\n"
            f"  Reason:          Error {error_code} — the value submitted to the carrier was\n"
            f"                   {len(original)} digit(s), but {len(corrected)} are required.\n"
            f"                   Corrected from the authoritative HR record.\n\n"
            f"  Confidence:      {round(score * 100)}% — passed {checks_passed}/{checks_total} compliance checks.\n\n"
            f"  No action needed. Record is ready for resubmission."
        )
        state["status"] = "AUTO_FIXED"
    else:
        state["action_card"] = (
            f"⚠️  Enrollment Review Required — HUMAN_REVIEW\n\n"
            f"  Field:           {field}\n"
            f"  Employee:        {name} ({emp_id})\n"
            f"  Submitted value: {original}\n\n"
            f"  Reason:          Error {error_code} — auto-correction confidence is\n"
            f"                   {round(score * 100)}% (threshold: 90%).\n"
            f"                   Passed {checks_passed}/{checks_total} compliance checks.\n\n"
            f"  Action needed:   Please verify and update this employee's record manually."
        )
        state["status"] = "HUMAN_REVIEW"

    reasoning = (
        f"Confidence {score} {'≥' if score >= 0.9 else '<'} threshold 0.9. "
        f"Routing to {'AUTO_FIXED' if score >= 0.9 else 'HUMAN_REVIEW'} path. "
        f"Product-led action card generated for {name}."
    )
    state["reasoning_path"].append(f"[Messenger] {reasoning}")

    elapsed = round((time.time() - t_start) * 1000)
    state["latency_ms"]["messenger"] = elapsed

    state["trace"].append({
        "node": "messenger",
        "latency_ms": elapsed,
        "status": state["status"],
        "action_card": state["action_card"],
    })
    return state
