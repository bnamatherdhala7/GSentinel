# GSentinel — Product Walkthrough

---

## Summary

Benefits enrollment rejections are mostly fixable without a human. The correct value — the right zip code, the right plan code, the right SSN format — is sitting in the HR record. The carrier rejected the submission because what was submitted didn't match it. That gap is mechanical, not ambiguous.

GSentinel is a 4-agent pipeline that closes that gap automatically: it reads the carrier rejection, looks up the correct value in the HR record, validates it against the enrollment schema, and either resolves the case in under 2 seconds or routes it to a human reviewer with a fully-populated context card showing exactly what the agent found and why it couldn't fix it.

---

## 1. Business Context

A full-suite SMB HR and payroll platform expanding into PEO services. The brokerage business is one of the largest in the SMB market. The PEO offering is the most strategic new bet — FY26 is foundation, FY27 is differentiated customer experience at scale.

The PEO promise is to own the full employer-of-record relationship: HR, payroll, benefits, and compliance under one roof. That includes what happens after benefit selections are made — implementing plans with carriers, fulfilling enrollments, and giving customers visibility.

Benefits ops is still heavily manual. Carrier rejection notices arrive. Someone reads them, decodes the error code, finds the correct value in the HR system, and manually resubmits. At broker scale, this is a recurring support cost. At PEO scale, where the platform is the employer of record, this is a liability with SLA consequences.

---

## 2. Problem Identification

### How I Found It

Three signals pointed at the same problem:

**Support ticket patterns.** Rejection resolution showed up in the top 5 inbound HR admin issues every enrollment cycle. The pattern was consistent: wrong zip, wrong DOB format, wrong plan code in the EDI 834 submission. Each took 20–45 minutes to resolve manually. The same errors recurred the next enrollment cycle.

**A broker conversation.** One mid-size benefits broker managing ~25 SMB clients was running roughly 40 support tickets per month on rejection resolution. All of it was the same 5–6 error codes. He had a spreadsheet. He wanted to not have the spreadsheet.

**Competitive audit.** Every incumbent platform — Ease, Rippling, Benefitfocus — surfaces the rejection. None of them correct it. The platform shows the admin the error code and stops there.

### Why It Matters for PEO

For a PEO specifically, the employer of record handles carrier rejections on behalf of its clients. Today that means manual processing by benefits ops staff. The ops headcount scales with client growth. Auto-correction converts that into a one-time engineering investment — the pipeline handles 10,000 clients the same way it handles 10.

---

## 3. Discovery

### Who the Customer Is

**HR generalists at SMBs (50–500 employees):** one to three people managing the full people function. During open enrollment, they're handling hundreds of enrollments simultaneously. A single carrier rejection can take 30–45 minutes to decode, fix, and resubmit.

**Benefits brokers managing 10–50 SMB clients:** absorbing rejection resolution on their clients' behalf. Effectively running a concierge service for errors that, in most cases, have a single correct answer.

**Benefits ops at the PEO platform (Phase 2):** handling carrier rejections manually on behalf of employer-of-record clients. Same problem, 100x the volume, SLA accountability.

### What Discovery Found

Conversations with HR admins and brokers revealed a consistent workflow: receive notice → decode error code (Google, carrier companion guide, or tribal knowledge) → find the correct value in the HR system → manually resubmit. The tools never shortened that workflow. They just displayed the rejection and waited.

The more important finding was about the errors themselves. They are not random. They cluster into types where the correct answer is always recoverable from the HR record — zip code typos, SSN format mismatches, plan codes that don't match the carrier's active list. The question was not whether this could be automated. It was why it hadn't been.

| Discovery method | What it surfaced |
|----------------|-----------------|
| Support ticket analysis | Top 5 pain point, every enrollment cycle |
| Broker interviews (n=2) | 40+ tickets/month, same error codes repeatedly |
| HR admin interviews (n=3) | 20–45 min per rejection, same manual workflow |
| Carrier companion guide audit | Error codes are carrier-specific; patterns are universal |
| Competitive analysis | Every incumbent shows the error; none correct it |

---

## 4. Solution & Trade-offs

### What We Built

A 4-agent LangGraph pipeline:

```
Carrier Rejection Notice
        │
        ▼
   Parser        Reads unstructured rejection text. Extracts employee ID,
                 error code, field affected, submitted value. Retrieves
                 matching explanation from carrier error KB. [LLM]
        │
        ▼
   Healer        DB-only lookup. Finds the correct value from the HR record.
                 Never calls an LLM. Pre-flags cases where source data is
                 also wrong — routes those to human review before Critic.
        │
        ▼
   Critic        3 hardcoded checks: field format, blocked placeholder values,
                 data type. All regex and rule-based. No inference.
        │
   ≥0.9 / <0.9
        │
   Messenger     Threshold routing. AUTO_FIXED card or HUMAN_REVIEW card
                 with full agent reasoning, Healer finding, and check results.
        │
   logs/agent_trace.json — complete audit trail, every run
```

### The Core Architectural Decision

The default instinct was to give the rejection notice to an LLM and ask it to suggest a fix. That approach was rejected early.

LLMs are appropriate for reading and reasoning over unstructured text. They are not appropriate for correcting financial and identity fields. The risk is asymmetric: a wrong zip code delays coverage. A wrong SSN is a compliance incident. "Probably right" is not good enough when the correct answer is sitting in the authoritative HR record.

The Healer uses code-only DB lookup. The corrected value always comes from the HR record. The LLM is walled off from financial fields by design. This is not a v1 limitation — it's a permanent architectural boundary.

The trade-off: cases where the HR record is also wrong, or where the correction requires carrier-specific judgement, cannot be auto-corrected. They go to HUMAN_REVIEW with full context. That is the right behavior — every AUTO_FIXED result is defensible because the source is traceable.

### What We Chose Not to Build

| Rejected option | Why |
|----------------|-----|
| LLM correction for all fields | Can't audit a hallucinated SSN |
| No-code workflow (n8n, Zapier) | No conditional routing; no audit trail |
| Batch EDI 834 resubmission | Requires carrier API contracts; Phase 2 |
| HRIS live integration | Real-time dependency adds fragility; Phase 3 |

### Error Code Prioritization

| Error | How common | Deterministic fix | Risk if wrong | Decision |
|-------|-----------|:---------------:|:-------------:|---------|
| 402 — zip code | Very high | ✅ | Low | AUTO_FIXED |
| 610 — SSN format | High | ✅ | Medium | AUTO_FIXED |
| 308 — plan code | High | ✅ | Medium | AUTO_FIXED |
| 209 — coverage tier | Medium | ✅ | Medium | AUTO_FIXED |
| 415 — dependent DOB | Medium | ❌ source also wrong | Medium | HUMAN_REVIEW |
| 501 — duplicate enrollment | Low | ❌ requires judgement | High | HUMAN_REVIEW |
| 716 — QLE window expired | Low | ❌ carrier exception needed | High | HUMAN_REVIEW |

---

## 5. Execution

### Cross-functional Dependencies

| Function | What they owned |
|----------|-----------------|
| Engineering | LangGraph pipeline, API, frontend |
| Benefits Ops | Error code taxonomy, carrier companion guide research, validation rules |
| Legal / Compliance | Liability scope for auto-corrections; audit trail requirements |
| CX / Support | Action card language — reviewed with support reps before shipping |
| Brokers (external) | Discovery interviews; error taxonomy validation |

### What Worked

**Scoping out non-deterministic corrections early.** The constraint — if we can't trace the corrected value to an authoritative source, we don't auto-correct — made every subsequent design decision faster. We never relitigated it.

**The HUMAN_REVIEW card turned out to be more valuable than expected.** We treated it as a fallback. HR admins in testing treated it as the most useful thing the product did. They had never seen a tool explain *why* a case was routed to them — what the agent found, what checks it ran, and what information would resolve it. The HUMAN_REVIEW path is a product, not an error state.

**The audit trail became a trust unlock with enterprise buyers.** Showing `agent_trace.json` — every decision, every DB lookup, every latency — addressed the "how do I know the AI isn't guessing?" concern before it was raised.

### What Didn't Work

**The Healer tried to infer corrections for Error 415 in the first version.** When the dependent DOB in the HR record was also malformed, an early version attempted to infer a plausible correct date. It was occasionally wrong in ways that were hard to catch. We replaced it with the correct behavior: if the source is also bad, pre-flag to HUMAN_REVIEW. The simpler rule was more reliable and more auditable.

**Carrier companion guide variability was underestimated.** The mock uses a single `standard_enr.json`. In production testing, the same field has different validation rules across carriers — Blue Shield SSN format vs. a regional carrier's format. Per-carrier schema maps are a Phase 2 requirement we hadn't fully scoped.

**Error 716 (QLE window) revealed a nuance we missed.** We assumed QLE window expiry was a clear route-to-human case. Some carriers accept late QLE enrollments with a letter of explanation. The card currently says "exception required" without telling the admin what that exception looks like or how to file it. This needs carrier-specific exception templates in Phase 2.

---

## 6. Results

### Primary Metric

**Auto-fix rate:** % of incoming rejections resolved with no human touch.

5 of 8 demo scenarios auto-fix — 63% auto-fix rate. Production target is ≥ 67% within 12 months, improving as we add error codes and per-carrier schemas.

### KPIs

**Leading (weekly)**

| Metric | Target |
|--------|--------|
| Pipeline runs per active customer | ≥ 5/week |
| Auto-fix rate per deterministic code | ≥ 90% |
| Time to action on HUMAN_REVIEW cases | < 4 hours |
| Admin override rate on AUTO_FIXED | < 5% |

**Lagging (monthly)**

| Metric | Target |
|--------|--------|
| Carrier re-rejection rate on AUTO_FIXED records | < 2% |
| HR admin time recovered | ≥ 4 hours/week per team |
| Pilot-to-paid conversion | ≥ 60% |

**Guardrails (never degrade)**

| Metric | Threshold |
|--------|-----------|
| Incorrectly auto-corrected records submitted to carrier | 0 — circuit-break to HUMAN_REVIEW |
| Audit trail completeness | 100% of runs |
| Compliance checks before AUTO_FIXED | All 3 required |

### Business Case

A 200-person company processes ~20 rejections per enrollment cycle. Before: 20 × 35 min = 11.7 hours of manual work. After: 13 auto-fixed (< 2 sec each) + 7 HUMAN_REVIEW cases (5 min each with full context in front of them) = 35 minutes total.

At a broker managing 25 SMB clients: 40 monthly rejection tickets → ~5 requiring human attention.

At a PEO with 10,000 employer-of-record clients: the pipeline runs as internal ops tooling. Benefits ops headcount stops scaling with client growth.

---

## 7. What I'd Do Differently

**Build internal ops first, not the customer product.** For a PEO, the highest-value deployment is the benefits ops team handling carrier rejections across the employer-of-record portfolio. I'd validate the error taxonomy with real carrier data there before surfacing it as a customer-facing feature.

**Run carrier-specific discovery earlier.** The general problem was well-understood quickly. The carrier-specific validation rules weren't. That gap showed up as a production blocker and a Phase 2 requirement. It should have been scoped in Phase 1.

**Co-design the HUMAN_REVIEW card with HR admins.** We got to the right format through iteration. Starting with a working session around a live rejection notice would have shortened that.

**Treat Workers' Comp as Phase 1b.** WC claim rejections — policy number mismatches, class code errors, FEIN format — follow the same agentic pattern. It should have been a parallel workstream.

---

*GSentinel · v0.5 · April 2026 · github.com/bnamatherdhala7/GSentinel*
