# Changelog

All notable changes to GSentinel are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

---

## [0.4.0] — 2026-04-20

### Added

- **Rejection queue panel** — left-sidebar queue renders 6 mock rejections from `GET /api/queue`; clicking a row runs the pipeline for that scenario
- **Metric bar** — 4 live stats: rejections processed · AUTO_FIXED % · Human Review count · Avg processing time
- **Three demo scenarios** covering all production-relevant paths

  | Scenario | File | Error | Employee | Expected outcome |
  |----------|------|-------|----------|-----------------|
  | REJ-001 | `scenario_402.txt` | 402 — Invalid Zip | Jordan Smith | AUTO_FIXED · 95% · `8020 → 80201` |
  | REJ-002 | `scenario_415.txt` | 415 — Malformed DOB | Jordan Smith | HUMAN_REVIEW · Riley Smith DOB invalid |
  | REJ-003 | `scenario_501.txt` | 501 — Duplicate | Morgan Lee | HUMAN_REVIEW · duplicate of EMP003-A |

- **Human Review card** (`renderHumanReviewCard`) — amber-bordered panel with field/employee/issue/suggested kv-table, plain-English reason block, and three action buttons: **Confirm**, **Override**, **Escalate**
- **`POST /api/resolve`** endpoint — accepts `rejection_id`, `action`, optional `override_value`; appends `human_resolver` node to `logs/agent_trace.json`
- **`POST /api/run`** — migrated from GET; accepts `RunRequest(scenario_file: Optional[str])` to select scenario
- **PENDING state** — clicking REJ-005 or REJ-006 (no scenario file) shows "Scenario not yet available" without running the pipeline

### Changed

- `data/internal_db.json` — EMP002 gains second dependent Riley Smith with malformed `dob: "2021-13-40"`; EMP003 gains `duplicate_flag: true` and `duplicate_of: "EMP003-A"`
- `data/knowledge/carrier_errors.md` — Error 415 section retitled "Missing or Malformed Date of Birth" with cross-reference guidance
- `graph/nodes.py` — healer pre-flags non-fixable scenarios (415 bad DB DOB, 501 duplicate) by setting `confidence_score = 0.5`; critic detects pre-flag and skips all 3 validation checks
- `messenger_node` — dedicated action card templates for error codes 415 and 501 with specific dependent name and duplicate record ID
- `frontend/index.html` — two-column layout (queue sidebar + main content), version badge updated to `v0.4 · Queue + Human Review`

### Added (docs)

- `docs/prd.md` — VP-level Product Requirements Document with market sizing ($8.42B TAM), competitor gap matrix, 6 OKRs, and 4-phase release plan

---

## [0.3.0] — 2026-04-20

### Added

- **Enterprise reasoning layer** — every node now emits a plain-English internal monologue entry to `state["reasoning_path"]`
- **RAG simulation** (`parser_node`) — scans full document for all candidate employee IDs and error codes before selecting primary; stores verbatim KB evidence in `state["kb_evidence"]`
- **Jailbreak & Compliance Guard** (`critic_node`) — 3 explicit checks per field correction

  | Check | What it tests |
  |-------|--------------|
  | Format guard | Regex from `schema/standard_enr.json` |
  | Jailbreak guard | Value not in blocked sentinel list (`00000`, `99999`, `11111`, `12345`, `00001`) |
  | Injection guard | Numeric fields must be all-digit |

- **Search-depth audit trail** (`healer_node`) — logs every DB record scanned as `Record[idx] → ✓ MATCH / ✗ skip`
- **Mismatch log** — verbatim diff of DB value vs. carrier-submitted value per field
- **Latency tracking** — `state["latency_ms"]` dict records wall-clock time per node; `500ms` deliberate think pause in parser and healer for UI breathing room
- **Safety & Compliance Report** — `build_compliance_report()` in `sentinel.py` prints node latencies, DB scan depth, check results, and KB evidence char count
- **UI Reasoning Path tab** — third panel gains three tabs: Agent Trace · Compliance · Reasoning Path; Compliance tab shows latency table, check list, mismatch log, and KB evidence; Reasoning Path shows 4-step internal monologue
- `state.py` additions: `latency_ms: dict`, `kb_evidence: str`, `reasoning_path: list`

### Changed

- Frontend version badge: `v0.3 · RAG + Compliance Guard`
- Parser node detail panel gains RAG candidates tag list
- Healer node detail panel gains search_depth checklist and mismatch log box
- Critic node detail panel gains pattern_tested, per-check ✓/✗ log, and summary box

---

## [0.2.0] — 2026-04-19

### Added

- **Visual web UI** (`frontend/index.html`) — single-page pipeline visualizer
  - Animated 4-node pipeline with live `idle → running → done` state transitions
  - Per-node input/output inspection panel — click any node to inspect
  - Confidence meter (0–100% bar), correction summary (submitted vs. corrected), action card display
  - Full agent trace log rendered in the browser from `logs/agent_trace.json`
  - Dark-mode, zero external dependencies

- **FastAPI server** (`api.py`) — REST API + static file host

  | Endpoint | What it returns |
  |----------|----------------|
  | `GET /api/run` | Executes the full pipeline, returns per-step timing, inputs, outputs |
  | `GET /api/trace` | Returns the last written agent trace |
  | `GET /api/db` | Returns the employee HR database |
  | `GET /api/raw-input` | Returns the raw carrier rejection text |

- **CONTRIBUTING.md** — Gitflow branching strategy, commit message format, PR process
- **CHANGELOG.md** — versioned change history (this file)
- **`develop` branch** — Gitflow integration branch; all features merge here before `main`

### Changed

- README rewritten in product-style: badges, hero statement, agent table with IO, architecture diagram, stack table

---

## [0.1.0] — 2026-04-19

### Added

- **LangGraph pipeline** (`sentinel.py`) — 4-node stateful DAG with conditional routing

  | Node | What it does |
  |------|-------------|
  | `parser_node` | Regex extraction from rejection text + knowledge base error lookup |
  | `healer_node` | Corrected value lookup from `internal_db.json` — no LLM guessing |
  | `critic_node` | Schema regex validation; sets `confidence_score` 0.95 (valid) or 0.5 (uncertain) |
  | `messenger_node` | Action card generation; routes to `AUTO_FIXED` or `HUMAN_REVIEW` |

- **`graph/state.py`** — `FulfillmentState` TypedDict and `FulfillmentStatus` enum (`AUTO_FIXED`, `HUMAN_REVIEW`, `NOTIFIED`)

- **Mock data**

  | File | Contents |
  |------|----------|
  | `data/internal_db.json` | 3 employee records: EMP001 (Alex Rivera), EMP002 (Jordan Smith), EMP003 (Morgan Lee) |
  | `data/knowledge/carrier_errors.md` | Plain-English reference for error codes 402, 415, 501, 308, 610 |
  | `mocks/carrier_logs/sample_error.txt` | Error 402 rejection for EMP002 — zip `8020` vs. correct `80201` |
  | `schema/standard_enr.json` | Enrollment validation schema with regex patterns |

- **Agent trace logging** — every node appends a structured entry to `logs/agent_trace.json` on each run
- **CLAUDE.md** — full build specification, hard rules, step-by-step construction guide

---

[Unreleased]: https://github.com/bnamatherdhala7/GSentinel/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/bnamatherdhala7/GSentinel/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/bnamatherdhala7/GSentinel/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bnamatherdhala7/GSentinel/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bnamatherdhala7/GSentinel/releases/tag/v0.1.0
