# GSentinel — Product Requirements Document

**`Market: $8.4B · CAGR: 11.1%`** · **`Target: SMBs 50–500 employees`** · **`Category: Agentic HR Automation`** · **`Status: v0.3 MVP`**

> Prepared for: VP of Product · April 2026

---

## 1. Summary

Benefits enrollment rejections are a silent operational tax on every SMB in America. When a carrier rejects an enrollment record over a 4-digit zip code, no one is automatically told, no system auto-corrects it, and the affected employee waits — sometimes weeks — for coverage that was already approved. GSentinel is an agentic fulfillment engine that reads raw carrier rejection notices, diagnoses the root cause, pulls the authoritative fix from internal HR records, validates it against the enrollment schema, and resolves it automatically — without human intervention, without LLM guessing on financial fields, and without routing through a no-code platform.

---

## 2. Contacts

| Name | Role | Responsibility |
|------|------|----------------|
| TBD | VP of Product | Executive sponsor, strategic alignment |
| TBD | Engineering Lead | Pipeline architecture, LangGraph graph design |
| TBD | Benefits Ops Lead | Carrier error taxonomy, validation rules |
| TBD | SMB Customer Lead | Customer discovery, pilot cohort |

---

## 3. Background

### The Problem Nobody Is Tracking

Every year, millions of EDI 834 enrollment transactions are rejected by insurance carriers. The rejections are not coverage disputes. They are **format errors** — a zip code that is 4 digits instead of 5, a date of birth formatted wrong, an SSN with a stray character. These errors are fully correctable from data that already exists in the employer's HR system.

But no tool fixes them automatically. Instead, they sit in a rejection queue. An HR admin — who is likely also running payroll, handling onboarding, and managing PTO — eventually opens the notice, manually cross-references the employee record, types the correction, and resubmits. At an SMB without a dedicated benefits ops team, this process takes **days**.

There is no industry-wide benchmark for EDI 834 rejection rates — **because the industry does not systematically track them.** That silence is not evidence the problem is small. It is evidence the problem is invisible. And invisible problems don't get fixed.

### The Numbers Behind the Problem

| Metric | Data | Source |
|--------|------|--------|
| HR time on administrative tasks at SMBs | **70%** of all HR capacity | Folks HR, 2026 survey of 450+ HR professionals |
| Benefits admin error rate | **13%** discrepancy between enrollment records and payroll records | U.S. Government Accountability Office |
| Claims denied due to admin / paperwork errors | **77% of all denials** are admin, not medical | KFF, 2024 ACA marketplace data |
| Average payroll corrections per period | **15 corrections** per payroll period | Ernst & Young |
| HR capacity headroom (SMBs) | **56%** of HR teams are understaffed | GoWorkwize, 2026 |
| HRIS adoption at SMBs | Only **18%** have a fully integrated HR management system | GoWorkwize, 2026 |
| Annual time saved with HR automation | **800+ hours/year** (~$25,000 in salary) | Stratus HR |

### Why This Keeps Happening

The root cause is a structural mismatch: insurance carriers accept enrollment data via **EDI 834 transactions**, each with their own companion guide specifying exact field formats. A record that is valid under the base HIPAA standard can be rejected by a specific carrier because their companion guide requires zip codes in a particular format, or dates in a particular layout. The broker knows. The carrier knows. The HR admin at a 120-person software company does not know — and no system automatically bridges the gap between the carrier's rejection notice and the employer's HR record.

---

## 4. Why Build This Now

### Three Conditions That Weren't True Two Years Ago

**1. Agentic pipelines are production-ready.**
LangGraph (released stable in 2024) gives us stateful, deterministic agent graphs with conditional routing. We can build a 4-node pipeline — parse, heal, validate, act — that runs end-to-end in under 2 seconds and never hallucinates a zip code, because the LLM never touches financial fields. The healer pulls from authoritative HR data only.

**2. SMB HR teams are at a breaking point.**
92% of organizations plan to increase AI investments over the next three years. 76% of HR leaders believe they will fall behind competitors if they don't adopt AI within 12–24 months. 65% of SMBs plan to adopt HR automation within the next year. The demand is there. The tools aren't.

**3. The market is fragmented and the gap at the SMB tier is real.**
The existing players — Ease, bswift, Benefitfocus, Rippling — were built for brokers, mid-market, or enterprise. None of them auto-correct carrier rejections. They surface the error. They don't fix it.

### The Market Timing

| Signal | Data |
|--------|------|
| Benefits admin software market size (2025) | **$8.42 billion** |
| YoY growth (2025 → 2026) | **$8.42B → $9.35B** (+11.1% CAGR) |
| Organizations prioritizing HR automation | **68%** cite it as a strategic goal |
| HR leaders planning AI investment increase | **92%** within 3 years |
| SMBs planning HR automation adoption | **67%** within next 12 months |
| HR professionals who feel ready for AI | Only **35%** — a trust and tooling gap |

Source: Research and Markets, GoWorkwize, Deel, 2025–2026.

---

## 5. Who We Are Building For

### Primary Segment: The Overwhelmed HR Generalist at a Growing SMB

**Company profile:** 50–500 employees. Series A–C tech, professional services, retail, or healthcare. One to three HR staff managing the full people function — recruiting, onboarding, payroll, benefits, compliance. No dedicated benefits ops role. No benefits coordinator. The HR team uses a basic HRIS (or spreadsheets) and a broker.

**Their job to be done:** Get new employees covered on day one of their benefits eligibility — without spending half the week chasing down carrier rejection notices, decoding carrier-specific error codes, and manually re-keying corrections.

**What they are doing today:**
1. Receive a PDF rejection notice from the carrier (sometimes days after submission)
2. Decode the error code manually (sometimes by Googling it)
3. Open the employee record in the HRIS and find the correct value
4. Log into the carrier portal and re-enter the corrected data
5. Hope the resubmission clears before the coverage effective date lapses

**The emotional cost:** Every day this sits unresolved is a day an employee thinks their benefits are active when they aren't. If they see a doctor on day 3 and the claim gets denied because the enrollment was never confirmed, that becomes an HR incident — not a carrier error.

### Secondary Segment: Benefits Brokers Managing 10–50 SMB Clients

Brokers are responsible for facilitating enrollment across their book of business. They are currently absorbing the operational cost of carrier rejections on behalf of their clients. An automated rejection-resolution layer directly reduces their support burden and makes them stickier to their clients.

### Who We Are Not Building For (v1)

| Excluded segment | Reason |
|-----------------|--------|
| Large enterprise (500+ employees) | Have dedicated benefits ops teams; different integration requirements |
| Individual consumers | No employer HR records to cross-reference |
| Insurance carriers | Different problem — they are the source of rejections, not the recipient |
| PEOs (Professional Employer Organizations) | Benefit from the same problem existing; complex incentive alignment |

---

## 6. Competitive Landscape

### The Honest Market Map

No competitor currently auto-corrects carrier enrollment rejections. They all surface the error. GSentinel is the only tool that closes the loop.

| Product | Tier | What They Do | What They Don't Do | Key Weakness |
|---------|------|-------------|-------------------|--------------|
| **Ease** | SMB / Broker | Benefits enrollment platform for brokers and small groups | No rejection auto-correction; surfaces errors only | Described as "clunky and not intuitive" even by brokers; UX consistently flagged as confusing |
| **Rippling** | SMB / Mid-Market | All-in-one HR platform with benefits module | Benefits and expense workflows described as "incomplete"; no rejection resolution | Opaque modular pricing — SMBs get charged for each add-on; support limited to admins only |
| **Benefitfocus** | Mid-Market / Enterprise | Enterprise benefits management and enrollment | Not designed for SMB; support turnaround can take months; high account manager churn | Built for large employers; SMB fit is weak by design |
| **bswift** | Mid-Market / Enterprise | Benefits administration and decision support | Enterprise-only; no direct SMB offering; no agentic correction | Too complex and expensive for sub-500 headcount |
| **Standard HRIS** (Bamboo, Paylocity, etc.) | SMB | HR records, payroll, benefits tracking | No carrier-facing automation; rejections require manual intervention | Records exist but are never connected to carrier feedback |

### The Gap GSentinel Fills

```
                    SURFACES          AUTO-CORRECTS
                    THE ERROR         THE ERROR
                       │                  │
Ease                   ✓                  ✗
Rippling               ✓                  ✗
Benefitfocus           ✓                  ✗
bswift                 ✓                  ✗
Standard HRIS          sometimes          ✗
                                          │
GSentinel              ✓                  ✓  ← only player
```

---

## 7. Value Proposition

### Customer Jobs We Address

| Job | Current pain | What GSentinel does |
|-----|-------------|---------------------|
| Resolve carrier rejection and resubmit | Manual: 20–45 min per rejection, spread over 1–3 days | Automatic: resolved in <2 seconds for deterministic errors |
| Know which rejections can be auto-fixed vs. need human review | No triage — all rejections land in the same queue | Critic node scores each correction; 90%+ confidence = AUTO_FIXED; <90% = routed for review |
| Audit trail for compliance | No log of what was changed, when, and why | Full agent trace written to `logs/agent_trace.json` on every run — auditable forever |
| Protect employees from coverage gaps | Coverage lapses silently when rejections aren't resolved in time | Immediate correction closes the window between rejection and resubmission |
| Prove the system isn't guessing | Black-box AI tools can't be trusted on financial data | Healer node uses DB lookup only — no LLM inference on zip codes, DOBs, or SSN fields |

### Gains Delivered

- **Time back:** 800+ hours/year estimate for a 200-person company (one full rejection correction per week, 20 minutes each, 50 weeks)
- **Coverage protection:** Employees don't experience a gap between their coverage start date and when the carrier confirms enrollment
- **Trust:** Every correction is traceable — who changed what, why, what the DB value was, what the carrier received
- **Zero guesswork:** Financial fields are never inferred — only pulled from authoritative HR records

### Pains Avoided

- Discovering a rejection 3 days later when the email surfaces from the carrier
- An employee filing a claim during a coverage gap caused by an unresolved rejection
- An HR admin re-keying the same zip code correction for the 12th time during open enrollment
- An audit finding where enrollment records don't match carrier records

---

## 8. Solution

### 8.1 How the Pipeline Works

```
Carrier Rejection Notice (raw text)
            │
            ▼
    ┌───────────────────┐
    │  Parser           │  RAG extraction — all candidate IDs and error codes
    │  (RAG Extractor)  │  ranked, primary record selected with reasoning
    └────────┬──────────┘
             │  { employee_id, error_code, field_affected, submitted_value }
             │  + kb_evidence (verbatim KB snippet)
             │  + reasoning_path entry
             ▼
    ┌───────────────────┐
    │  Healer           │  Internal DB lookup only — no LLM inference
    │  (DB Lookup)      │  search_depth audit: Record[0] ✗ → Record[1] ✓ MATCH
    └────────┬──────────┘
             │  { corrected_value, mismatch_log }
             ▼
    ┌───────────────────┐
    │  Critic           │  3-check Jailbreak & Compliance Guard
    │  (Compliance)     │  Check 1: format regex | Check 2: jailbreak sentinel
    └────────┬──────────┘  Check 3: injection guard
             │  { confidence_score: 0.95 | 0.7 | 0.5 }
        ┌────┴─────┐
     ≥ 0.9       < 0.9
        │           │
   AUTO_FIX    HUMAN_REVIEW
        │           │
        └─────┬─────┘
              ▼
    ┌───────────────────┐
    │  Messenger        │  Product-led action card:
    │  (Action Card)    │  Field · Change · Reason · Confidence
    └───────────────────┘
              │
              ▼
    logs/agent_trace.json  ←  full audit trail, every run
```

### 8.2 Key Features

| Feature | What it does | Why it matters |
|---------|-------------|----------------|
| **RAG extraction** | Parser scans the full rejection text for all candidate IDs and error codes before selecting the primary record | Handles multi-record rejection notices; shows its work |
| **DB-only Healer** | Correction values come exclusively from `internal_db.json` — the LLM never touches a zip code, DOB, or SSN | Financial field integrity — no hallucination risk |
| **3-check Compliance Guard** | Format regex + jailbreak sentinel list + injection guard — every corrected value must pass all three | Prevents a corrupted or adversarial value from being submitted to the carrier |
| **Graded confidence scoring** | 0.95 (all 3 checks pass) · 0.7 (format passes, others fail) · 0.5 (format fails) | Triage: high-confidence → auto-fix; low-confidence → human review queue |
| **Product-led action card** | Output includes Field, Change, Reason, and Confidence Level in plain English | HR admin understands what happened without reading a log file |
| **Full agent trace** | Every node appends a structured entry to `logs/agent_trace.json` on every run | Compliance, audit, and debugging — complete chain of custody |
| **Safety & Compliance Report** | Console and API output includes per-node latency, DB search depth, mismatch log, check results | Makes the invisible work visible for enterprise buyers |
| **Visual pipeline UI** | Animated 4-node web dashboard — node-by-node inspection, confidence meter, reasoning path tab | Demo and sales tool; also used in pilot customer onboarding |

### 8.3 Supported Error Codes (v1)

| Code | Carrier Error | Auto-fixable | DB Field |
|------|--------------|:------------:|---------|
| 402 | Invalid zip code | ✅ | `address.zip` |
| 415 | Missing / malformed date of birth | ✅ | `dob` |
| 610 | SSN format error | ✅ | `ssn_last4` |
| 501 | Duplicate enrollment | ❌ Human review | — |
| 308 | Invalid plan code | ❌ Human review | — |

### 8.4 Technology

| Layer | Choice | Constraint |
|-------|--------|-----------|
| Agent orchestration | LangGraph | Stateful DAG — no external workflow tools (n8n, Zapier, Make are prohibited) |
| Correction source | `internal_db.json` (HR records) | LLM must never infer financial fields |
| Validation | Python `re` + schema JSON | Rules are deterministic and auditable |
| API | FastAPI | REST + static file serving |
| Frontend | Vanilla HTML/CSS/JS | No build step, no third-party dependencies |

### 8.5 Assumptions

| Assumption | Risk if wrong |
|-----------|--------------|
| The employer's HR records contain the correct value that the carrier rejected | If HR records are also wrong, auto-correction produces a still-invalid record — Critic catches this via confidence degradation |
| Carrier rejection notices follow a consistent text format parseable by regex | Carriers that use PDFs, images, or proprietary portals require a different ingestion layer |
| Deterministic errors (format, length, type) represent the majority of rejections | If most rejections are actually eligibility disputes, the auto-fix rate drops significantly |
| SMB HR teams have access to the rejection notices in text form | Some carriers only surface rejections through a portal login, not email or file delivery |

---

## 9. Objective & Key Results

### Objective
Eliminate the manual correction loop for deterministic carrier enrollment rejections at SMBs — reducing time-to-resolution from days to seconds and giving HR teams back the capacity they've been spending on data entry.

### Key Results (12-month horizon)

| # | Key Result | Target | Measurement |
|---|-----------|--------|-------------|
| KR1 | Auto-fix rate for deterministic rejections | **≥ 85%** of Error 402, 415, 610 rejections resolved with no human touch | Pipeline status = `AUTO_FIXED` / total rejections processed |
| KR2 | Time-to-resolution | **< 5 seconds** end-to-end (from rejection ingestion to action card) | Pipeline `total_ms` across all runs |
| KR3 | Pilot customer adoption | **10 SMB customers** actively using GSentinel in production within 6 months | Active pipeline runs per customer per month |
| KR4 | HR admin time recovered | **≥ 4 hours/week** per customer team | Pre/post time-tracking survey with pilot cohort |
| KR5 | Compliance guard accuracy | **0 incorrectly auto-corrected records** submitted to carriers | Post-run audit: records where `AUTO_FIXED` but carrier re-rejected |
| KR6 | Audit trail completeness | **100%** of pipeline runs produce a complete `agent_trace.json` | Log file validation on every run |

---

## 10. Release Plan

### Phase 1 — MVP (Current: v0.3)

**Scope:** Single-rejection pipeline for the 3 most common deterministic error codes (402, 415, 610). Local data, single-tenant, manual ingestion of rejection text.

**Ships when:** 10 pilot customers can run the pipeline against their real rejection notices and confirm auto-corrections are accurate.

**What is NOT in Phase 1:**
- Real carrier API submission (correction is produced, not automatically resubmitted)
- Multi-rejection batch processing
- HRIS integration (Bamboo, Paylocity, etc.)
- Email or Slack notification delivery
- Authentication / multi-tenant

---

### Phase 2 — Carrier Integration

**Scope:** Direct EDI 834 file ingestion. Auto-resubmission of corrected records to carrier sandbox APIs. Support for 10+ error codes.

**Gate:** Phase 1 pilot shows ≥ 85% auto-fix accuracy rate and zero incorrectly-corrected records.

---

### Phase 3 — HRIS Connector

**Scope:** Live read from HRIS (Bamboo, Paylocity, Rippling via API). HR records are pulled in real time instead of from a static JSON file. Multi-tenant. Notifications (email, Slack) on completion.

**Gate:** Phase 2 proves carrier API resubmission is reliable across 3+ carriers.

---

### Phase 4 — Broker Dashboard

**Scope:** Multi-client view for benefits brokers. Aggregate rejection queue across their book of business. SLA tracking. White-label option.

**Gate:** 3+ broker relationships active; each managing 5+ SMB clients through GSentinel.

---

## 11. Out of Scope (Permanent)

- **Real-time LLM inference on financial fields** — zip codes, DOBs, SSNs, and premium amounts are never generated by the model. This is a hard rule, not a v1 limitation.
- **External no-code tools** — no n8n, Zapier, or Make. All orchestration is native LangGraph.
- **Third-party brand references** in UI or logs
- **Consumer-facing product** — this is an employer / broker tool

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Carrier rejection notices don't follow a consistent parseable format | Medium | High | Parser RAG layer handles multiple formats; unknown formats route to HUMAN_REVIEW not silent failure |
| HR records contain the same error as the submitted value | Low | High | Critic Compliance Guard catches mismatches; confidence degrades below 0.9 threshold |
| Pilot customers can't export rejection notices in text form | Medium | Medium | Phase 1 supports manual paste; Phase 2 adds email parsing and PDF ingestion |
| Auto-correction introduces a new error (e.g., DB has stale data) | Low | High | Full audit trail + carrier re-rejection feedback loop provides ground truth |
| Competitors copy the auto-correction approach | High (12-month horizon) | Medium | Speed of pilot execution and broker relationships create switching cost before incumbents ship |

---

## 13. Open Questions

| Question | Owner | Target answer date |
|---------|-------|------------------|
| What percentage of real-world rejections are Error 402 / 415 / 610 vs. other codes? | Benefits Ops Lead | End of Phase 1 pilot |
| Which carriers send machine-readable rejection notices vs. PDF/portal only? | Engineering Lead | Pre-Phase 2 |
| Are brokers willing to pay for a rejection-resolution layer, or does this need to be bundled with enrollment? | SMB Customer Lead | End of Q2 2026 |
| What is the liability exposure if an auto-correction produces a wrong value and the employee loses coverage? | Legal / VP Product | Pre-Phase 2 (before live resubmission) |

---

*GSentinel · April 2026 · The only benefits tool that doesn't just surface the rejection — it fixes it.*
