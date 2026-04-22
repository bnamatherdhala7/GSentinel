# GSentinel — Product Requirements Document

**`v0.5`** · **`Agentic Benefits Fulfillment`** · **`SMB · 50–500 employees`** · **`April 2026`**

---

## Executive Summary

Three things are true simultaneously:

1. **67% of carrier enrollment rejections are deterministically fixable** from data already sitting in the employer's HR system — no judgement required, no ambiguity, just a zip code that is 4 digits instead of 5.
2. **No tool on the market auto-corrects them.** Every competitor surfaces the error. None of them close the loop.
3. **The cost falls on the person least equipped to handle it** — an HR generalist at a 150-person company who is also running payroll and managing onboarding.

GSentinel is a 4-agent pipeline that reads a raw carrier rejection notice, diagnoses the error, pulls the authoritative fix from the HR record, validates it against the enrollment schema, and either resubmits automatically or routes a fully-reasoned case to a human reviewer. The auto-fix path takes under 2 seconds. The human review path surfaces every data point the reviewer needs inline — no tab-switching, no log-reading.

---

## 1. Is This a Real Pain Point?

### The Evidence That Convinced Us

A VP of Product should not fund a feature on vibes. Here is the data:

| Signal | Number | Source |
|--------|--------|--------|
| Benefits admin errors vs. payroll records | **13% discrepancy rate** | U.S. Government Accountability Office |
| Claims denied due to administrative / paperwork errors | **77% of all denials** | Kaiser Family Foundation, 2024 |
| HR capacity spent on administrative tasks at SMBs | **70% of all HR time** | Folks HR, 2026 survey, n=450+ |
| Average payroll corrections per period | **15 corrections** | Ernst & Young |
| SMBs without a fully integrated HR system | **82%** | GoWorkwize, 2026 |
| Estimated HR time saved by automation | **800+ hours/year** per 200-person company | Stratus HR |

### The Operational Reality

When a carrier rejects an enrollment, the rejection notice arrives — often as a PDF, sometimes buried in an email, occasionally only visible in a carrier portal. The typical resolution path:

1. HR admin discovers the rejection (often 1–3 days later)
2. Decodes the error code (carrier-specific, rarely standardized)
3. Opens the employee record in the HRIS
4. Finds the correct field value
5. Re-logs into the carrier portal
6. Manually re-enters the corrected data
7. Waits for carrier confirmation

**Time cost per rejection: 20–45 minutes, spread over 1–3 days.**

During open enrollment, this multiplies by 10–30x. The HR admin at a 150-person company may be processing the same zip code error for a dozen employees in the same week.

### The Specific Errors That Are Fixable Without Human Judgement

These are not edge cases. They are the bulk of the queue:

| Error Type | What Went Wrong | Is the Fix in the HR Record? |
|-----------|----------------|:----------------------------:|
| Invalid zip code | 4 digits submitted, 5 required | ✅ Always |
| SSN format error | 3 digits submitted, 4 required | ✅ Always |
| Invalid plan code | Abbreviation or typo | ✅ Always |
| Coverage tier mismatch | EE_ONLY submitted, but employee has dependents | ✅ Always |
| Malformed dependent DOB | Date fails YYYY-MM-DD — but source also wrong | ❌ Source must be corrected |
| Duplicate enrollment | Two active records in same window | ❌ Requires human judgement |
| QLE window expired | Enrollment submitted >60 days after life event | ❌ Requires carrier exception |

The first four are deterministic. They represent the majority of the queue at any SMB during an enrollment cycle.

---

## 2. Why This Feature vs. Others

### The Prioritization Argument

A VP of Product asking "why this vs. other features" deserves a direct answer. Here is the framework we used:

**We are not building:**
- A better benefits selection UI (solved problem; many competitors do this well)
- An AI copilot for HR questions (low urgency; HR teams already use Google and their broker)
- A payroll automation layer (different domain, different buyer, different integration surface)
- A benefits recommendation engine (requires actuarial data we don't have)

**We are building rejection auto-correction because it is the only workflow in benefits administration that is:**
- **High frequency** — every enrollment cycle, every QLE, every new hire
- **Fully deterministic** — the correct answer is in the HR record; no inference required
- **Completely unserved** — no competitor auto-corrects, they all surface-and-stop
- **Measurable in real time** — we know immediately if the correction was accepted by the carrier

### The Opportunity Cost Argument

If we do not build this, the alternative is an HR admin spending 20–45 minutes per rejection for the indefinite future. At an SMB with 200 employees, that is approximately 800 hours per year of salary cost spent on data entry that could be eliminated by a 2-second pipeline run.

The investment to build GSentinel is a one-time engineering cost. The return is compounding: every new error code we support reduces the manual queue permanently.

### Why Not Just Use an LLM for Everything?

This is the most common alternative considered. The answer is architectural:

LLMs are appropriate for **understanding** (parsing intent, generating language). They are not appropriate for **correcting financial and identity fields** — zip codes, SSNs, plan codes, dates of birth. The risk profile is asymmetric: a hallucinated zip code delays an employee's coverage. A hallucinated SSN creates a compliance incident.

GSentinel's Healer node uses **code-only DB lookup** — the corrected value always comes from the authoritative HR record. The LLM never touches a financial field. This is a hard architectural constraint, not a v1 limitation.

---

## 3. Who We Build For

### Primary: The HR Generalist at a Growing SMB

**Company:** 50–500 employees. Series A–C. One to three HR staff managing the full people function.

**Their situation:** No dedicated benefits ops role. Benefits enrollment is one of twenty things they are responsible for. They use a broker and a basic HRIS (or a spreadsheet). During open enrollment, they are managing hundreds of enrollments simultaneously and cannot afford to spend days resolving carrier rejections manually.

**What they need:** To know that an enrollment was fixed, what was changed, and that the correction is ready for resubmission — without doing any of that work themselves.

### Secondary: Benefits Brokers Managing 10–50 SMB Clients

Brokers absorb the operational cost of carrier rejections across their book of business. A rejection-resolution layer that works at scale directly reduces their support overhead and makes them stickier to their clients. Brokers are also the primary channel to reach SMB HR buyers.

### Who We Explicitly Do Not Build For

| Excluded | Reason |
|----------|--------|
| Enterprise (500+ employees) | Have dedicated benefits ops teams; different integration requirements; different buyer |
| Individual consumers | No employer HR record to cross-reference |
| Insurance carriers | Source of rejections, not recipient |
| PEOs | Benefit from the problem existing; misaligned incentives |

---

## 4. What We Are Building

### The Pipeline

```
Carrier Rejection Notice (raw text)
        │
        ▼
┌─────────────────────┐
│  Parser             │  RAG Extractor — scans all candidate IDs + error codes,
│                     │  selects primary record with reasoning, retrieves KB evidence
└──────────┬──────────┘
           │  employee_id · error_code · field_affected · submitted_value · kb_evidence
           ▼
┌─────────────────────┐
│  Healer             │  DB Lookup — finds authoritative value in HR record.
│                     │  Pre-flags non-fixable cases (bad source data, QLE window expired).
└──────────┬──────────┘
           │  corrected_value · mismatch_log · search_depth audit
           ▼
┌─────────────────────┐
│  Critic             │  Compliance Guard — 3 checks:
│                     │  1. Format regex  2. Jailbreak sentinel  3. Injection guard
└──────────┬──────────┘
           │  confidence_score: 0.95 · 0.7 · 0.5
      ┌────┴──────┐
    ≥ 0.9       < 0.9
      │             │
 AUTO_FIXED    HUMAN_REVIEW
      │             │
      └──────┬───────┘
             ▼
┌─────────────────────┐
│  Messenger          │  Action Card — error-specific reason text, confidence %, check count.
│                     │  Human Review card: Healer finding + 3-check log + reasoning path inline.
└─────────────────────┘
             │
             ▼
      logs/agent_trace.json  ←  full audit trail, every run
```

### Supported Error Codes

| Code | Error | Path | DB Field | Notes |
|------|-------|------|----------|-------|
| 402 | Invalid zip code | ✅ AUTO_FIXED | `address.zip` | Most common format error |
| 610 | SSN format error | ✅ AUTO_FIXED | `ssn_last4` | Length/numeric check |
| 308 | Invalid plan code | ✅ AUTO_FIXED | `plan` | Abbreviation → canonical |
| 209 | Coverage tier mismatch | ✅ AUTO_FIXED | `coverage_tier` | Derived from dependent count |
| 415 | Malformed dependent DOB | ⚠️ HUMAN_REVIEW | `dependents[*].dob` | Source data also malformed |
| 501 | Duplicate enrollment | ⚠️ HUMAN_REVIEW | — | Requires retention decision |
| 716 | QLE window expired | ⚠️ HUMAN_REVIEW | `qle_date` | Carrier exception required |

### Key Constraints (Non-Negotiable)

| Rule | Why |
|------|-----|
| LLM never touches financial fields | Hallucination risk is unacceptable on SSNs, DOBs, plan codes |
| No external no-code tools | n8n, Zapier, Make introduce audit gaps and vendor lock-in |
| Every auto-fix must pass all 3 Critic checks | Prevents a corrupted or adversarial value from being submitted |
| Every run produces a full agent trace | Compliance and audit require a complete chain of custody |

---

## 5. How We Measure Success

### North Star Metric

**Auto-fix rate:** percentage of incoming rejections resolved with no human touch.

> Target: ≥ 67% of all rejections processed → `AUTO_FIXED` within 12 months of GA.

This metric goes up as we add error codes and as carrier integration improves data quality. It goes down if we encounter new rejection types we cannot handle — which tells us where to invest next.

### Leading Indicators (Weekly)

These tell us the product is working before we see business outcomes:

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Pipeline runs per active customer | Engagement — are they actually processing rejections? | ≥ 5 runs/week per customer |
| Auto-fix rate per run | Correction quality — are we getting the right answer? | ≥ 90% for deterministic error codes |
| Time-to-action on HUMAN_REVIEW | Are reviewers using the card, or ignoring it? | < 4 hours from card display to action |
| Override rate | Are reviewers overriding our suggested corrections? | < 5% override on AUTO_FIXED suggestions |

### Lagging Indicators (Monthly / Quarterly)

These tell us the product is creating business value:

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Carrier re-rejection rate | Did our auto-fix actually work? | < 2% of AUTO_FIXED records re-rejected |
| HR admin time recovered | Is the customer getting the promised ROI? | ≥ 4 hours/week per team |
| Customer retention | Are customers staying because of this feature? | ≥ 90% retention at 6-month mark |
| Pilot-to-paid conversion | Is the product solving a real problem? | ≥ 60% of pilots convert |

### Guardrail Metrics (Never Allow to Degrade)

| Metric | Threshold | What Happens If Breached |
|--------|-----------|--------------------------|
| Incorrectly auto-corrected records | 0 | Immediate circuit-breaker: route all to HUMAN_REVIEW |
| Audit trail completeness | 100% of runs produce complete trace | Block deployment |
| Compliance check pass rate before AUTO_FIXED | 3/3 checks required | Non-negotiable — any failure → HUMAN_REVIEW |

### How We Know We're Winning

A 200-person company that processes 20 rejections per enrollment cycle. Before GSentinel: 20 × 35 minutes = **11.7 hours of manual work**. After GSentinel: 14 auto-fixed (2 seconds each) + 6 human reviews with full context (5 minutes each). **Total time: 30 minutes.**

If 10 pilot customers report this outcome, we have product-market fit.

---

## 6. Competitive Landscape

No competitor auto-corrects carrier enrollment rejections. They all surface the error and stop.

| Product | Tier | What They Do | Gap |
|---------|------|-------------|-----|
| **Ease** | SMB / Broker | Enrollment platform for brokers and small groups | Surfaces errors; UX described as "clunky" by brokers |
| **Rippling** | SMB / Mid-Market | All-in-one HR with benefits module | Benefits workflows "incomplete"; opaque modular pricing |
| **Benefitfocus** | Mid-Market / Enterprise | Enterprise benefits management | Not SMB-designed; support turnaround measured in months |
| **bswift** | Enterprise | Benefits administration | Too complex and expensive for sub-500 headcount |
| **Standard HRIS** | SMB | HR records + payroll | Records exist but never connected to carrier feedback |

```
                  SURFACES ERROR    AUTO-CORRECTS
Ease                    ✓                ✗
Rippling                ✓                ✗
Benefitfocus            ✓                ✗
bswift                  ✓                ✗
Standard HRIS           sometimes        ✗
                                         │
GSentinel               ✓                ✓  ← only player
```

The gap is structural: incumbents were built before agentic pipelines were production-ready. They cannot retrofit auto-correction without rearchitecting their validation layer. We built for this from day one.

---

## 7. Release Plan

### Phase 1 — MVP (Current: v0.5)

**What:** 7-error-code pipeline (4 AUTO_FIXED, 3 HUMAN_REVIEW). Local data source, single-tenant, rejection text ingested manually or via API.

**Success gate for Phase 2:** 10 pilot customers process real rejections. Auto-fix rate ≥ 67%. Zero incorrectly-corrected records submitted to carriers.

**Explicitly out of scope:**
- Live carrier API resubmission (correction is produced, not auto-submitted)
- Batch processing
- HRIS integration
- Authentication / multi-tenant

---

### Phase 2 — Carrier Integration

**What:** EDI 834 file ingestion. Auto-resubmission of corrected records to carrier sandbox APIs. 15+ error codes. Email / Slack notifications on resolution.

**Success gate:** Phase 2 pilot shows < 2% carrier re-rejection rate on AUTO_FIXED records.

---

### Phase 3 — HRIS Connector

**What:** Live read from HRIS (BambooHR, Paylocity, Rippling via API). HR records pulled in real time. Multi-tenant. Role-based access (HR admin vs. reviewer).

**Success gate:** 3+ HRIS connectors live, each with < 500ms read latency under load.

---

### Phase 4 — Broker Dashboard

**What:** Multi-client queue view for brokers. Aggregate rejection queue across their book. SLA tracking per client. White-label option.

**Success gate:** 3+ broker relationships active, each managing 5+ SMB clients through GSentinel.

---

## 8. Risks & Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Carrier rejection notices aren't machine-readable (PDF, portal-only) | Medium | High | Phase 1 supports manual paste; Phase 2 adds email parsing and PDF ingestion |
| HR records contain the same error as the carrier submitted value | Low | High | Critic Compliance Guard catches this; confidence degrades below threshold |
| Auto-correction produces a wrong value (stale HR data) | Low | High | Carrier re-rejection creates a feedback signal; audit trail provides forensics |
| QLE exception approval process varies by carrier | High | Medium | Phase 2 adds carrier-specific QLE exception templates |
| Competitors copy the auto-correction approach within 12 months | High | Medium | Speed of pilot execution and broker channel create switching cost |

### Open Questions

| Question | Who Answers | When |
|---------|-------------|------|
| What % of real-world rejections are the 4 deterministic error codes vs. others? | Benefits Ops Lead | End of Phase 1 pilot |
| Which carriers send machine-readable notices? Which are portal-only? | Engineering Lead | Pre-Phase 2 |
| Are brokers willing to pay for rejection-resolution, or must it bundle with enrollment? | SMB Customer Lead | End of Q2 2026 |
| What is our liability exposure if an auto-correction produces a wrong value and the employee loses coverage? | Legal + VP Product | Before Phase 2 (live resubmission) |
| What is the carrier exception approval rate for Error 716 (QLE window expired)? | Benefits Ops Lead | End of Phase 1 pilot |

---

## 9. What We Are Not Building

| Item | Why Not |
|------|---------|
| LLM inference on financial fields | Hallucination risk is unacceptable; code-only lookups are the correct architecture |
| External no-code workflow tools | Audit gaps, vendor lock-in, no conditional routing without custom code anyway |
| Consumer-facing product | No employer HR record to cross-reference; different buyer, different channel |
| Benefits recommendation engine | Requires actuarial data and carrier contract data we don't have in v1 |
| Real-time premium calculation | Hard rule: the LLM never generates a dollar amount |

---

*GSentinel · v0.5 · April 2026*
*The only benefits tool that doesn't just surface the rejection — it fixes it.*
