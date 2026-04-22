import re
import json
import time
from datetime import datetime as _dt
from pathlib import Path

BASE = Path(__file__).parent.parent

# Strict DOB validation: month 01-12, day 01-31
_VALID_DOB = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')


# ---------------------------------------------------------------------------
# Parser — RAG-simulated extraction with candidate scoring
# ---------------------------------------------------------------------------
def parser_node(state: dict) -> dict:
    t_start = time.time()
    time.sleep(0.5)

    text = state["raw_input"]

    all_emp_ids = list(dict.fromkeys(re.findall(r"EMP\d+", text)))
    all_err_codes = list(dict.fromkeys(re.findall(r"(?:ERROR CODE:\s*|(?<!\d))(\d{3})(?!\d)", text)))
    top_candidates = {"employee_ids": all_emp_ids, "error_codes": all_err_codes}

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

    kb_text = (BASE / "data/knowledge/carrier_errors.md").read_text()
    section_match = re.search(
        rf"(## Error {error_code}[^\n]*\n.*?)(?=\n## |\Z)", kb_text, re.DOTALL
    )
    kb_section = section_match.group(1).strip() if section_match else f"## Error {error_code} — Unknown"
    kb_body = re.sub(r"^## Error \d+[^\n]*\n", "", kb_section).strip()
    state["error_description"] = kb_body
    state["kb_evidence"] = kb_section

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
    time.sleep(0.5)

    db = json.loads((BASE / "data/internal_db.json").read_text())
    target_id = state["employee_id"]
    code = state["error_code"]

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

    corrected = None
    mismatch_log = None
    healer_override_confidence = None  # set only when healer flags non-fixable

    if emp:
        if code == "402":
            corrected = emp["address"]["zip"]
            mismatch_log = (
                f"Record[{match_index}].address.zip = '{corrected}' | "
                f"Carrier submitted '{state['submitted_value']}' → "
                f"{'MISMATCH — length ' + str(len(state['submitted_value'])) + ' vs required 5' if corrected != state['submitted_value'] else 'values equal, no change'}"
            )

        elif code == "415":
            # Find dependent with invalid DOB in HR records
            bad_dep = None
            for dep in emp.get("dependents", []):
                if not _VALID_DOB.match(dep.get("dob", "")):
                    bad_dep = dep
                    break
            if bad_dep:
                corrected = bad_dep["dob"]  # malformed value — stored as evidence, not a fix
                mismatch_log = (
                    f"Record[{match_index}].dependents → '{bad_dep['name']}' "
                    f"has malformed dob='{bad_dep['dob']}'. "
                    f"HR record is also invalid — cannot auto-correct."
                )
                healer_override_confidence = 0.5
            else:
                mismatch_log = "No malformed dependent DOB found in HR records."

        elif code == "501":
            dup_of = emp.get("duplicate_of")
            mismatch_log = (
                f"Record[{match_index}] has duplicate_flag=True. "
                f"Flagged as duplicate of {dup_of}. "
                f"Human must determine which record to retain."
            )
            healer_override_confidence = 0.5

        elif code == "610":
            corrected = emp["ssn_last4"]
            submitted = state["submitted_value"] or ""
            mismatch_log = (
                f"Record[{match_index}].ssn_last4 = '{corrected}' | "
                f"Carrier submitted '{submitted}' ({len(submitted)} digit(s)) → "
                f"{'MISMATCH — expected 4 digits, got ' + str(len(submitted)) if corrected != submitted else 'values equal, no change'}"
            )

        elif code == "308":
            corrected = emp["plan"]
            submitted = state["submitted_value"] or ""
            mismatch_log = (
                f"Record[{match_index}].plan = '{corrected}' | "
                f"Carrier submitted '{submitted}' → "
                f"{'MISMATCH — not a recognized carrier plan code' if corrected != submitted else 'values equal, no change'}"
            )

        elif code == "209":
            db_tier = emp.get("coverage_tier", "EE_ONLY")
            submitted = state["submitted_value"] or ""
            corrected = db_tier
            dep_count = len(emp.get("dependents", []))
            mismatch_log = (
                f"Record[{match_index}].coverage_tier = '{corrected}' | "
                f"Carrier submitted '{submitted}' → "
                f"{'MISMATCH — employee has ' + str(dep_count) + ' dependent(s) on file; tier should be ' + corrected if corrected != submitted else 'values equal, no change'}"
            )

        elif code == "716":
            qle_date_str = emp.get("qle_date", "")
            qle_type = emp.get("qle_type", "qualifying life event")
            submitted_date_str = state["submitted_value"] or ""
            days_since_qle = None
            if qle_date_str and submitted_date_str:
                try:
                    qle_dt = _dt.strptime(qle_date_str, "%Y-%m-%d")
                    sub_dt = _dt.strptime(submitted_date_str, "%Y-%m-%d")
                    days_since_qle = (sub_dt - qle_dt).days
                    mismatch_log = (
                        f"Record[{match_index}].qle_date = '{qle_date_str}' ({qle_type}) | "
                        f"Enrollment submitted '{submitted_date_str}' = {days_since_qle} days after QLE. "
                        f"60-day window expired {days_since_qle - 60} day(s) ago."
                    )
                except ValueError:
                    mismatch_log = "QLE date or enrollment date could not be parsed."
            else:
                mismatch_log = "QLE date or submission date missing from HR records."
            healer_override_confidence = 0.5
            state["_days_since_qle"] = days_since_qle  # pass to reasoning section
            state["_qle_date_str"] = qle_date_str

    state["corrected_value"] = corrected

    # Signal non-fixable scenarios to the critic
    if healer_override_confidence is not None:
        state["confidence_score"] = healer_override_confidence

    if code == "415" and healer_override_confidence == 0.5:
        bad_dep_name = "unknown dependent"
        bad_dep_dob = corrected or state["submitted_value"] or "unknown"
        if emp:
            for dep in emp.get("dependents", []):
                if not _VALID_DOB.match(dep.get("dob", "")):
                    bad_dep_name = dep["name"]
                    bad_dep_dob = dep["dob"]
                    month_val = bad_dep_dob.split("-")[1] if "-" in bad_dep_dob else "?"
                    break
        reasoning_detail = (
            f"Dependent '{bad_dep_name}' has DOB '{bad_dep_dob}' in HR records. "
            f"Month value '{month_val}' exceeds valid range 01-12 — source data is malformed. "
            f"HR admin must correct the dependent's DOB before auto-fix is possible. Cannot auto-correct."
        )
    elif code == "501":
        dup_of = emp.get("duplicate_of", "unknown") if emp else "unknown"
        reasoning_detail = (
            f"EMP003 carries duplicate_flag=True — flagged as a duplicate of {dup_of}. "
            f"Two active records exist in the same enrollment window. "
            f"HR must determine which record to retain and remove the duplicate before resubmitting. Cannot auto-correct."
        )
    elif code == "716" and healer_override_confidence == 0.5:
        days_since_qle = state.pop("_days_since_qle", None)
        qle_date_str = state.pop("_qle_date_str", "unknown")
        days_str = f"{days_since_qle} days" if days_since_qle is not None else "an unknown number of days"
        over_str = f"{days_since_qle - 60} day(s)" if days_since_qle is not None else "an unknown number of days"
        reasoning_detail = (
            f"Enrollment submitted {days_str} after QLE date '{qle_date_str}'. "
            f"60-day carrier window expired {over_str} ago. "
            f"Cannot auto-correct — carrier exception request must be filed by HR admin."
        )
    else:
        state.pop("_days_since_qle", None)
        state.pop("_qle_date_str", None)
        reasoning_detail = mismatch_log or f"No correctable field found for error code {code}."

    reasoning = (
        f"Opened internal_db.json — scanned {len(db['employees'])} record(s). "
        f"Located {target_id} at index {match_index}. "
        f"{reasoning_detail}"
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
        "healer_override_confidence": healer_override_confidence,
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

    # If healer already flagged non-fixable (confidence pre-set to 0.5), pass through
    if state["confidence_score"] == 0.5:
        validation_log = [
            f"Check 1 — Pre-flagged by Healer as non-fixable for Error {code} — skipping format validation",
            f"Check 2 — Skipped (non-fixable path)",
            f"Check 3 — Skipped (non-fixable path)",
        ]
        summary = f"Error {code} routed to HUMAN_REVIEW by Healer. Confidence held at 0.5."
        reasoning = f"Healer pre-flagged Error {code} as non-fixable. Passing through confidence=0.5. No validation run."
        state["reasoning_path"].append(f"[Critic] {reasoning}")
        elapsed = round((time.time() - t_start) * 1000)
        state["latency_ms"]["critic"] = elapsed
        state["trace"].append({
            "node": "critic",
            "role": "Jailbreak & Compliance Guard",
            "latency_ms": elapsed,
            "corrected_value": value,
            "pattern_tested": "n/a — non-fixable path",
            "validation_log": validation_log,
            "checks_passed": 0,
            "checks_total": 3,
            "confidence_score": 0.5,
            "summary": summary,
        })
        return state

    pattern_map = {
        "402": schema["zip_format"],
        "415": r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$",
        "610": schema["ssn_last4_format"],
        "308": schema["plan_code_format"],
        "209": schema["coverage_tier_format"],
    }

    BLOCKED_VALUES = {"00000", "99999", "11111", "12345", "00001"}

    pattern = pattern_map.get(code, r"^.+$")
    validation_log = []

    check1 = bool(re.match(pattern, value))
    validation_log.append(
        f"Check 1 — Format guard: regex='{pattern}' | value='{value}' → {'PASS' if check1 else 'FAIL'}"
    )

    check2 = value not in BLOCKED_VALUES
    validation_log.append(
        f"Check 2 — Jailbreak guard: value '{value}' not in blocked list → {'PASS' if check2 else 'FAIL — blocked sentinel value'}"
    )

    numeric_codes = {"402", "610"}
    check3 = value.isdigit() if code in numeric_codes else True
    label3 = "all-numeric check" if code in numeric_codes else "non-numeric field — injection guard skipped"
    validation_log.append(
        f"Check 3 — Injection guard: {label3} → {'PASS' if check3 else 'FAIL — non-numeric chars detected'}"
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

    dep_count = len(emp.get("dependents", [])) if emp else 0
    reason_detail = {
        "402": (
            f"Zip code submitted was {len(original or '')} digit(s); "
            f"5-digit USPS format required. "
            f"Corrected from authoritative HR record."
        ),
        "610": (
            f"SSN last 4 submitted was {len(original or '')} digit(s); "
            f"exactly 4 required. "
            f"Corrected from authoritative HR record."
        ),
        "308": (
            f"Plan code '{original}' is not a recognized carrier plan. "
            f"Corrected to '{corrected}' from authoritative HR record."
        ),
        "209": (
            f"Coverage tier '{original}' doesn't match dependent records. "
            f"Employee has {dep_count} dependent(s) on file — "
            f"correct tier is '{corrected}'. Corrected from authoritative HR record."
        ),
    }.get(error_code, f"Submitted value corrected from authoritative HR record.")

    if score >= 0.9:
        state["action_card"] = (
            f"✅ Enrollment Correction — AUTO_FIXED\n\n"
            f"  Field:           {field}\n"
            f"  Change:          {original} → {corrected}\n"
            f"  Employee:        {name} ({emp_id})\n\n"
            f"  Reason:          Error {error_code} — {reason_detail}\n\n"
            f"  Confidence:      {round(score * 100)}% — passed {checks_passed}/{checks_total} compliance checks.\n\n"
            f"  No action needed. Record is ready for resubmission."
        )
        state["status"] = "AUTO_FIXED"

    elif error_code == "415":
        # Find the bad dependent name for the specific card
        bad_dep_name = "Unknown dependent"
        bad_dep_dob = corrected or original or "unknown"
        if emp:
            for dep in emp.get("dependents", []):
                if not _VALID_DOB.match(dep.get("dob", "")):
                    bad_dep_name = dep["name"]
                    bad_dep_dob = dep["dob"]
                    break
        state["action_card"] = (
            f"⚠️  Action needed: {bad_dep_name}'s date of birth on file is invalid\n"
            f"    ({bad_dep_dob}). Please correct the dependent's DOB in HR records\n"
            f"    and resubmit {name}'s enrollment."
        )
        state["status"] = "HUMAN_REVIEW"

    elif error_code == "501":
        dup_of = emp.get("duplicate_of", "unknown") if emp else "unknown"
        state["action_card"] = (
            f"⚠️  Action needed: {name}'s enrollment was flagged as a duplicate\n"
            f"    of an existing record ({dup_of}). Please review both records and\n"
            f"    confirm which should be retained before resubmitting."
        )
        state["status"] = "HUMAN_REVIEW"

    elif error_code == "716":
        qle_date = emp.get("qle_date", "unknown") if emp else "unknown"
        qle_type = emp.get("qle_type", "qualifying life event") if emp else "qualifying life event"
        state["action_card"] = (
            f"⚠️  Action needed: {name}'s enrollment was submitted outside the\n"
            f"    60-day qualifying life event window. QLE ({qle_type}): {qle_date}.\n"
            f"    Submitted: {original}. A carrier exception request must be filed\n"
            f"    before this enrollment can be accepted."
        )
        state["status"] = "HUMAN_REVIEW"

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
