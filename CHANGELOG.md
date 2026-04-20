# Changelog

All notable changes to GSentinel are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

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

[Unreleased]: https://github.com/bnamatherdhala7/GSentinel/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/bnamatherdhala7/GSentinel/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bnamatherdhala7/GSentinel/releases/tag/v0.1.0
