# GSentinel — Product Walkthrough
### Principal PM Interview · Benefits & PEO · 30-minute Project Review

---

## TL;DR

Benefits enrollment rejections are a silent operational tax on every SMB in America. 67% of them are deterministically fixable from data already in the HR system — no judgement required. No tool on the market auto-corrects them. GSentinel is a 4-agent pipeline that does exactly that: reads the rejection notice, finds the correct value in the HR record, validates it against the enrollment schema, and either resolves it automatically or hands a fully-reasoned case to a human reviewer in under 2 seconds.

This is the kind of agentic operations problem that becomes **10x more valuable inside a PEO**, where the platform owns every carrier relationship, processes rejections at portfolio scale, and carries SLA liability as the employer of record.

---

## 1. Business Context

**The company:** A full-suite SMB HR and payroll platform expanding into Professional Employer Organization (PEO) services. The brokerage business is one of the largest serving the SMB market. The PEO offering is the most strategic new bet — FY26 is foundation, FY27 is differentiated customer experience at scale.

**What they're working toward:** The PEO promise — bundle HR, payroll, benefits, and compliance under one employer-of-record relationship. The platform now "owns what happens after benefit selections are made: implementing plans with carriers, fulfilling enrollments, and giving customers visibility into the status of their benefits."

**The operational reality today:** Benefits ops is still heavily manual. Carrier rejection notices arrive. Someone has to read them, decode the error code, find the correct value in the HR system, and manually resubmit. At broker scale, this is a customer support cost. At PEO scale, where the platform is the employer of record, **this is a liability.**

**How GSentinel fits:** Phase 1 is a carrier rejection auto-correction pipeline for the SMB broker channel. Phase 2 is the same pipeline embedded as internal benefits ops tooling for the PEO platform — where processing speed and audit trail quality become SLA requirements, not nice-to-haves.

---

## 2. Problem Identification

### How I Identified It

The problem surfaced from three signals converging:

**Signal 1 — Support ticket taxonomy.** Looking at the most common inbound HR admin complaints, rejection resolution appeared in the top 5 every enrollment cycle. The pattern was always the same: "I got a rejection notice. I don't know what the code means. I fixed it manually. It happened again next week for someone else."

**Signal 2 — Broker operations conversation.** One mid-size benefits broker managing ~25 SMB clients described spending 40+ support tickets per month on rejection resolution. Every ticket was a zip code, SSN, or plan code that was wrong in the submitted EDI 834 file. The fix took 20 minutes. The pattern repeated every enrollment cycle.

**Signal 3 — Competitive audit.** Every platform in the market — Ease, Rippling, Benefitfocus — surfaces the error. None of them auto-correct it. The rejection notice arrives, the platform shows it to the admin, and that is where the product's help ends.

### How It Ladders to Company Goals

For a benefits platform: rejection resolution directly impacts **carrier confirmation rates**, which directly impacts **coverage activation timing**, which is the metric employees actually experience. A carrier rejection that sits for 3 days means 3 days of coverage limbo.

For a PEO platform specifically: the platform is the employer of record. When a carrier rejects an enrollment, the PEO's benefits ops team handles it manually today. Auto-correction converts a scaling operational cost into a one-time engineering investment. Every new client adds to the portfolio without adding to the ops headcount.

---

## 3. Discovery

### Who the Customer Is

**Primary:** HR generalists at SMBs (50–500 employees) — one to three people managing the full people function. During open enrollment, they are processing hundreds of enrollments simultaneously. They cannot afford to spend a day resolving a zip code error.

**Secondary:** Benefits brokers managing 10–50 SMB clients — absorbing the operational cost of rejection resolution on behalf of their clients. They are also the primary channel to reach SMB HR buyers.

**Internal (Phase 2):** Benefits ops specialists at the PEO platform — today handling carrier rejections manually on behalf of employer-of-record clients.

### What I Found in Discovery

Three conversations shaped the design:

**HR admin (120-person tech company):** "I don't even look at the rejection code. I just Google it, find the carrier's companion guide, and compare it to what I entered. It's always something dumb — a zip code or a date format. It takes me 30 minutes every time and I don't know why the system can't just check this before submitting."

**Benefits broker (25-client book):** "I'm basically running a rejection concierge service. My clients can't decode carrier error codes. I have a spreadsheet of the 12 most common ones. I pull it up, fix it, resubmit. I'd love to not do that."

**HR admin (300-person healthcare company):** "During open enrollment we get 15–20 rejections in a week. I have a checklist. It's the same mistakes every year. Zip codes, DOBs for new dependents, and occasionally someone submits the wrong plan code. Every single one requires me to log into the carrier portal separately."

### Key Discovery Insight

The errors are not random. They cluster into **7 deterministic types** where the correct value is always recoverable from the HR record. The question was never "can this be automated" — it was "has anyone built the automation." The answer was no.

| Discovery method | What it revealed |
|----------------|-----------------|
| Support ticket analysis | Top 5 pain, every enrollment cycle |
| Broker interviews (n=2) | 40+ tickets/month, same 5 error codes |
| HR admin interviews (n=3) | 20–45 min per rejection, consistent manual workflow |
| Carrier companion guide audit | Error codes are carrier-specific but patterns are universal |
| Competitive analysis | Every incumbent surfaces errors; none correct them |

---

## 4. Solution & Prioritization Trade-offs

### What We Built

A 4-agent LangGraph pipeline: **Parser → Healer → Critic → Messenger**

```
Carrier Rejection Notice
        │
        ▼
   Parser        RAG extraction — all candidate IDs + error codes ranked;
                 KB evidence from carrier_errors.md retrieved
        │
        ▼
   Healer        DB-only lookup — never calls an LLM on a financial field.
                 Pre-flags non-fixable cases before reaching Critic.
        │
        ▼
   Critic        3-check Compliance Guard: format regex · jailbreak sentinel · injection guard
        │
   ≥0.9 / <0.9
        │
   Messenger     Error-specific action card. Human Review card shows full reasoning inline.
        │
   logs/agent_trace.json  ←  full audit trail, every run
```

### Key Architectural Decision: Why 4 Agents, Not One LLM

The first instinct was: give a capable LLM the rejection notice and ask it to suggest a fix. This was rejected explicitly and early.

**Why:** LLMs are appropriate for understanding and language. They are not appropriate for correcting financial and identity fields — zip codes, SSNs, DOBs, plan codes. The risk profile is asymmetric: a hallucinated zip code delays coverage. A hallucinated SSN is a compliance incident.

The Healer node uses **code-only DB lookup**. The corrected value always comes from the authoritative HR record. The LLM never touches a financial field. This is a hard architectural constraint that we built from day one, not a v1 limitation.

**Trade-off accepted:** This means GSentinel cannot correct errors that require inference or contextual judgement. It routes those to human review instead. That is a feature, not a limitation — it means every AUTO_FIXED correction is defensible in an audit.

### What We Chose NOT to Build

| Rejected option | Why |
|----------------|-----|
| LLM correction for all fields | Financial field integrity risk; not auditable |
| No-code workflow (n8n, Zapier) | No conditional routing without custom code; audit gaps |
| Batch EDI 834 resubmission | Requires carrier API contracts; out of scope for Phase 1 |
| HRIS live integration | Adds a real-time dependency that increases fragility; deferred to Phase 3 |
| Workers' comp claims processing | Same agentic pattern applies; scoped out for Phase 1 focus |

### Prioritization Framework for Error Codes

Not all errors were equal. We prioritized by:
1. **Frequency** — how often does this error type appear in real queues?
2. **Determinism** — is the correct answer always recoverable from the HR record?
3. **Risk** — what is the consequence of an incorrect auto-correction?

| Error | Frequency | Deterministic | Risk if wrong | Decision |
|-------|-----------|:-------------:|:-------------:|---------|
| 402 — zip code | Very high | ✅ | Low | Phase 1 AUTO_FIXED |
| 610 — SSN format | High | ✅ | Medium | Phase 1 AUTO_FIXED |
| 308 — plan code | High | ✅ | Medium | Phase 1 AUTO_FIXED |
| 209 — coverage tier | Medium | ✅ | Medium | Phase 1 AUTO_FIXED |
| 415 — dependent DOB | Medium | ❌ (source also wrong) | Medium | Phase 1 HUMAN_REVIEW |
| 501 — duplicate | Low | ❌ (requires judgement) | High | Phase 1 HUMAN_REVIEW |
| 716 — QLE window | Low | ❌ (carrier exception required) | High | Phase 1 HUMAN_REVIEW |

---

## 5. Execution

### Who I Worked With

| Function | Role in the project |
|----------|---------------------|
| Engineering | LangGraph pipeline architecture, API design, frontend |
| Benefits Ops | Error code taxonomy, carrier companion guide research, validation rules |
| Legal / Compliance | Liability framework for auto-corrections; audit trail requirements |
| CX / Support | Action card language — tested with support reps before shipping |
| Brokers (external) | Discovery interviews + validation of error taxonomy |

### What Went Well

**The deterministic scope constraint was the right call.** Deciding early to scope out non-deterministic corrections meant we never had to debate "should we let the LLM guess this?" It made every subsequent design decision faster and cleaner.

**The human review card became the most valuable output.** We originally thought human review was a fallback. In practice, the HR admins in testing said the Human Review card — which shows the Healer Finding, all 3 compliance checks, and the full agent reasoning path inline — was more useful than anything they'd had before. They always knew *why* a case was routed to them, and what to do about it.

**The compliance audit trail was a trust unlock.** Showing enterprise-minded buyers the full `agent_trace.json` — every decision, every DB lookup, every validation check, every latency — addressed the "how do I know the AI isn't guessing?" question before it was asked.

### What Didn't Go Well

**The first version of the Healer tried to be too smart.** The initial design attempted to infer the correct value for cases where the HR record was also wrong (Error 415 — malformed dependent DOB). The inference was confident but occasionally wrong in unexpected ways. We shipped the simpler and correct behavior: if the source data is also bad, route to human review. Don't try to fix what you can't fix.

**We underestimated carrier companion guide variability.** The mock uses a single `standard_enr.json` schema. In production testing with real carrier data, we found that the same field (e.g., SSN last 4) has different validation rules depending on the carrier. Blue Shield wants exactly 4 digits; a regional carrier wants 9-digit format with dashes stripped. This created a Phase 2 requirement we hadn't fully scoped: per-carrier schema maps.

**The QLE window scenario (Error 716) revealed a discovery gap.** We assumed QLE window expiry was a clear-cut "route to human review" case. In practice, brokers told us some carriers will accept late enrollments with a letter of explanation. We hadn't built a mechanism to surface that nuance — the card just says "exception required." This needs a carrier-specific exception template in Phase 2.

### Key Risks Encountered

| Risk | What happened | How addressed |
|------|--------------|--------------|
| HR records contain the same error as the submitted value | Discovered in Error 415 testing | Healer pre-flags; Critic passes through; HUMAN_REVIEW with full context |
| Carrier companion guide drift between carriers | Found in production validation | Scoped as Phase 2: per-carrier schema map |
| LLM hallucination on edge cases | Prevented by architecture | Code-only DB lookup; LLM never touches financial fields |
| False confidence in auto-corrections | Theoretical at v0.5 | 3-check Compliance Guard + carrier re-rejection as ground truth |

---

## 6. Results & Impact

### North Star Metric

**Auto-fix rate:** % of incoming rejections resolved with no human touch.

> Current: 5 of 8 demo scenarios resolve automatically — **63% auto-fix rate**. Production target: ≥ 67% within 12 months.

This metric improves as we add error codes and improve carrier-specific schemas. It degrades if we encounter rejection types we can't handle — which tells us exactly where to invest next.

### KPI Framework

**Leading indicators (weekly — are we working?)**

| Metric | Target |
|--------|--------|
| Pipeline runs per active customer | ≥ 5 runs/week |
| Auto-fix rate for deterministic codes | ≥ 90% per code |
| Time-to-action on HUMAN_REVIEW cases | < 4 hours from display to action |
| Override rate on AUTO_FIXED suggestions | < 5% |

**Lagging indicators (monthly — are we creating value?)**

| Metric | Target |
|--------|--------|
| Carrier re-rejection rate on AUTO_FIXED records | < 2% |
| HR admin time recovered | ≥ 4 hours/week per team |
| Pilot-to-paid conversion | ≥ 60% |
| Customer retention at 6 months | ≥ 90% |

**Guardrail metrics (never allow to degrade)**

| Metric | Threshold |
|--------|-----------|
| Incorrectly auto-corrected records submitted to carrier | 0 → circuit-breaker to HUMAN_REVIEW |
| Audit trail completeness | 100% of runs produce complete trace |
| Compliance checks before AUTO_FIXED | 3/3 required — any failure = HUMAN_REVIEW |

### Business Impact Framing

A 200-person company processes ~20 rejections per enrollment cycle. Before: 20 × 35 min = **11.7 hours of manual work**. After: 13 auto-fixed (< 2 sec each) + 7 HUMAN_REVIEW cases (5 min each with full context) = **35 minutes total**.

At a broker managing 25 SMB clients: 40 monthly tickets → ~5 tickets requiring human attention. The broker gets back **35 support tickets per month**.

At a PEO platform with 10,000 employer-of-record clients: the same pipeline runs as internal ops tooling. Benefits ops headcount does not scale with client growth.

---

## 7. Key Takeaways

**1. The scoping constraint was the product.** Deciding that GSentinel would never guess a financial field — and would always route uncertain cases to a human with full context — was not a limitation. It was the reason enterprise buyers trusted it. The most important product decisions were about what we would refuse to do.

**2. Human review is a product, not a fallback.** The Human Review card ended up being more valued than the auto-fix in early testing. HR admins had never seen a tool that explained *why* a case was routed to them, what the agent tried, and what specific data would resolve it. The HUMAN_REVIEW path is a product experience, not an error state.

**3. Discovery found the pattern; execution found the exceptions.** Interviews told us the problem was real and the error codes were consistent. Building the product found the edge cases — malformed source data, carrier-specific validation rules, QLE exception processes. These are not reasons to not build; they are the Phase 2 roadmap.

**4. Audit trail is a sales tool.** The compliance tab and reasoning path were designed for debugging. In practice, they became the most effective demo element for cautious enterprise buyers. "Show me what the AI decided and why" is the first question any compliance-minded buyer asks. Having a complete answer built into the product is a moat.

---

## 8. What I'd Do Differently

**Start with internal ops, not the customer product.** For a PEO platform specifically, the highest-value deployment is not customer-facing — it's internal. The benefits ops team handling carrier rejections for 10,000 employer-of-record clients is the same problem at 100x scale with SLA accountability. I'd build GSentinel as an internal ops tool first, validate the error taxonomy with real carrier data, and then surface it as a customer-facing feature once the auto-fix rate is above 85%.

**Run carrier-specific discovery earlier.** I spent too much time on the general problem (carrier rejections are manual, HR admins hate them) and not enough time on carrier-specific companion guide research. The Blue Shield validation rule for SSN format is different from the Anthem rule. That's not a v2 problem — it's a v1 data problem that showed up as a production blocker.

**Design the HUMAN_REVIEW UX with actual HR admins in the room.** The Human Review card was designed based on what we assumed admins needed. It worked well in testing, but we got there by iteration, not by co-design. Starting with a 2-hour working session with 3 HR admins around a live rejection notice would have gotten us to the right card format 2 iterations faster.

**Scope Workers' Comp as Phase 1b, not Phase 3.** The same agentic pattern — parse notice, validate against source record, auto-correct or route — applies directly to Workers' Comp claim rejections (policy number mismatches, class code errors, FEIN format). The error taxonomy is different but the pipeline is identical. It should have been a parallel workstream, not a future phase.

---

## 9. How This Connects to the Gusto Role

The role owns "what happens after benefit selections are made: implementing plans with carriers, fulfilling enrollments, and giving customers visibility." That is precisely the problem GSentinel solves.

The strategic context is PEO: as Gusto becomes the employer of record for its PEO clients, carrier rejection resolution moves from a customer support cost to a platform liability. The same pipeline that auto-corrects zip codes for an SMB HR admin becomes the infrastructure that keeps Gusto's benefits ops team from scaling headcount linearly with client growth.

**Phase 1 (current):** Broker/SMB channel — HR admins get auto-corrections and Human Review cards. 63–67% auto-fix rate.

**Phase 2 (PEO):** Internal ops tooling — benefits ops specialists get the same pipeline as a workflow automation layer. Every carrier rejection across the PEO portfolio runs through the same 4-agent pipeline. SLA tracking per client. Exception templates for QLE and COBRA cases. Per-carrier schema maps for the 50+ carrier integrations.

**Phase 3 (differentiated PEO experience):** Customer-facing visibility layer for PEO employer clients — real-time status of every pending enrollment, auto-fix notifications, and a human review queue for cases that require employer input.

The architecture is the same at every phase. The surface changes. The agent pipeline, the compliance guard, and the audit trail are the durable infrastructure.

---

## Appendix — Anticipated Questions

**"How did you prioritize 7 error codes vs. adding more?"**
Frequency × determinism × risk. The 4 AUTO_FIXED codes cover the majority of the queue. The 3 HUMAN_REVIEW codes cover the cases that genuinely require judgement. Everything else is Phase 2.

**"Why not use an LLM to handle the human review cases too?"**
We tried early prototypes. The issue isn't LLM capability — it's auditability. If a dependent's DOB in the HR record is also malformed, a capable LLM might infer a plausible correct date. But "plausible" is not "authoritative." If the carrier re-rejects the enrollment because the inferred DOB was wrong, we have no defensible audit trail. Better to route to human with full context and let the correct answer come from the source.

**"What would the PEO version of this look like operationally?"**
Internal queue instead of customer queue. Benefits ops specialists instead of HR admins. Per-carrier SLA tracking. COBRA and QLE exception templates. The Human Review card becomes an internal case management tool. The audit trail becomes evidence for carrier disputes.

**"How does this relate to Workers' Comp?"**
Same agentic pipeline, different error taxonomy. WC claim rejections cluster around policy number format, employer class code mismatches, and FEIN validation — all deterministic, all recoverable from source records. Phase 1b candidate.

**"What's the biggest risk you haven't solved?"**
Per-carrier schema drift. We currently validate against a single `standard_enr.json`. In production, every carrier has its own companion guide with field-specific validation rules that change when the carrier updates their systems. Phase 2 requires a carrier-keyed schema map and a change-detection process when companion guides update.

---

*GSentinel · v0.5 · April 2026 · github.com/bnamatherdhala7/GSentinel*
