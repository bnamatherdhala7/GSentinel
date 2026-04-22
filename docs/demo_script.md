# GSentinel — Demo Script
### For: Hiring Manager / Technical Interview / VP of Product
### Runtime: ~8 minutes | Format: Live walkthrough at http://localhost:8000

---

## Before You Start

**Have open in advance:**
- Browser at `http://localhost:8000` (server running: `uvicorn api:app --port 8000`)
- This script on a second screen or printed

**One-line pitch to open with:**
> "GSentinel is an agentic pipeline that reads raw insurance carrier rejection notices, diagnoses the root cause, pulls the authoritative fix from your HR database, and either resolves it automatically or hands a fully-reasoned case to a human — in under 2 seconds."

---

## Act 1 — Set the Scene (60 seconds)

**Say:**
> "The problem I'm solving is specific: every time a benefits enrollment gets rejected by an insurance carrier, someone in HR has to read the rejection notice, find the employee record, verify the correct value, and manually resubmit. At a company with 2,000 employees, that's dozens of these a month — each one a manual ticket.

> The research says 67% of these rejections are deterministically fixable from data already sitting in your HR system. The gap isn't intelligence — it's automation. That's what GSentinel closes."

**Point to the screen:**
> "What you're looking at is a live rejection queue. Six carrier rejections came in this morning. Four were auto-resolved before anyone touched them. Two need a human decision. Let me walk you through each case."

---

## Act 2 — The 3 Auto-Fixed Cases (3 minutes)

### Case 1: Invalid Zip Code — Error 402

**Click:** REJ-001 (Jordan Smith · E-402 · address.zip)

**Wait for the green AUTO_FIXED card to appear, then say:**
> "Jordan Smith's zip code was submitted to the carrier as `8020` — four digits instead of five. The agent read the rejection notice, looked up the authoritative zip in the HR database, and confirmed `80201` is the correct value. Three compliance checks ran — format regex, jailbreak guard, injection guard — all passed. Confidence: 95%. Auto-fixed. No human touched this."

**Point to the pipeline nodes at the top:**
> "You can see each of the four agents that ran: Parser extracted the facts from the raw text, Healer pulled the correct value from the database, Critic validated it against the enrollment schema, Messenger wrote the action card and routed it. Click any node to inspect exactly what went in and came out."

---

### Case 2: SSN Format Error — Error 610

**Click:** REJ-005 (Morgan Lee · E-610 · ssn_last4)

**Wait for the green AUTO_FIXED card, then say:**
> "Same pattern, different field. Morgan Lee's SSN last 4 came in as `910` — three digits. The HR record has `9104`. Healer found it, Critic confirmed the four-digit regex match, 95% confidence. Auto-fixed.

> Notice the action card text is different from the zip code case — the system generates error-specific language, not a generic message. That matters for any reviewer who spot-checks these."

---

### Case 3: Invalid Plan Code — Error 308

**Click:** REJ-006 (Alex Rivera · E-308 · plan_code)

**Wait for the green AUTO_FIXED card, then say:**
> "Third auto-fixable case. Alex Rivera's plan code was submitted as `GLD_PPO` — an abbreviation the carrier doesn't recognize. The HR record has the canonical value: `GOLD_PPO`. The Critic validates this against a plan_code_format regex from the enrollment schema. Passed. Fixed.

> Three different error types, three different fields, same pipeline. That's the point — the agents are generalized, the fix logic is deterministic and extensible."

---

## Act 3 — The Human Review Cases (2.5 minutes)

### Case 4: Malformed Dependent DOB — Error 415

**Click:** REJ-002 (Jordan Smith · E-415 · dependents[1].dob)

**Wait for the amber HUMAN_REVIEW card, then say:**
> "This one is different. Jordan Smith has a dependent — Riley Smith — whose date of birth in the HR record is `2021-13-40`. Month 13 doesn't exist. This isn't a data entry error on the carrier side, it's an error in the source HR record itself.

> The agent can't auto-correct this, and it *shouldn't* — the authoritative source is also wrong. So instead of guessing, it flags the specific dependent, explains the exact failure, and routes it for human review."

**Point to the card sections:**
> "Three things I want you to notice in this card.

> First — the Healer Finding. It tells the reviewer exactly what it found: `Riley Smith DOB 2021-13-40, month 13 exceeds valid range 01-12`. Not 'date of birth error' — the specific field, the specific value, the specific reason.

> Second — the Compliance Checks. You can see each of the three validation steps with a pass, fail, or skip icon. In this case, the Healer pre-flagged it as non-fixable, so all three checks are marked as skipped — correctly.

> Third — scroll down to Agent Reasoning Path. Four tagged entries, one per agent, showing the internal monologue. The reviewer doesn't have to switch to another tab — all of this is inline in the card."

**Point to the action buttons:**
> "The reviewer has three options: Confirm the suggested fix if one exists, Override with a manual value, or Escalate to a benefits administrator. Every action is logged to the audit trail."

---

### Case 5: Duplicate Enrollment — Error 501

**Click:** REJ-003 (Morgan Lee · E-501 · enrollment_id)

**Wait for the amber card, then say:**
> "Last case. Morgan Lee's enrollment ID was already submitted in this enrollment window — the HR record is flagged as a duplicate of `EMP003-A`. Someone needs to decide which record to keep and which to tombstone. That's a judgement call, not a lookup.

> The agent surfaces the duplicate reference immediately and offers the escalation path. No ticket created, no email sent — the reviewer sees it the moment they click the queue item."

---

## Act 4 — The Engineering Layer (1.5 minutes)

**Click:** The Compliance tab (top right of the trace panel)

**Say:**
> "If you want to see what's happening under the hood — this is the compliance tab. Per-node latency, the mismatch log showing exactly what the carrier submitted versus what the HR record has, and the full validation log with each check.

> Total pipeline time for a clean auto-fix is about 1,100 milliseconds. Most of that is intentional — each agent has a 500ms think pause built in so the UI animation is readable. In a production batch context you'd strip those."

**Click:** The Reasoning tab

**Say:**
> "And this is the reasoning path — the internal monologue. Four steps, one per agent. The Parser explains which candidate employee IDs and error codes it found and why it selected the ones it did. The Healer explains which database records it scanned. The Critic explains what it tested and what passed. The Messenger explains the routing decision.

> Every run writes this to `logs/agent_trace.json`. Full audit trail, always.

> The reason this matters for enterprise: you can't ship an agentic system that makes financial corrections without being able to explain every decision. This is the mechanism."

---

## Act 5 — Close (30 seconds)

**Say:**
> "To recap what you've seen:

> Four deterministic agents. Three auto-fixable error types — zip code, SSN format, plan code — all resolved at 95% confidence with no human involvement. Two non-fixable error types — malformed source data, duplicate records — routed to human review with full reasoning inline.

> 67% of the rejection queue resolved automatically. Human time spent only on cases that genuinely require judgement.

> The pipeline is extensible — adding a new error code means adding one `elif` block in the Healer and one pattern in the schema. The compliance guard and audit trail come for free.

> Happy to go deeper on any layer — the agent state design, the compliance check architecture, or the product decision behind routing vs. auto-fixing."

---

## Appendix — Questions You May Get

**"Why not just use an LLM to fix everything?"**
> "LLMs are great at understanding. They're not appropriate for correcting financial and identity fields — SSNs, plan codes, dates of birth. Those require authoritative source lookup, not inference. The Healer never calls an LLM. The fix always comes from the database."

**"How would this scale to real carriers?"**
> "The Parser stage would be replaced with a carrier API adapter — the rest of the pipeline is identical. The agent state and compliance contracts don't change. That's the architecture advantage of separating extraction from correction from validation."

**"What's the false positive risk on auto-fixes?"**
> "The Critic runs three independent checks. If any fail, confidence drops below the 0.9 threshold and the case routes to human review. The jailbreak guard specifically catches sentinel values that look valid but aren't — `00000`, `99999`, `12345`. A case never gets auto-fixed unless it passes all three checks."

**"Why LangGraph?"**
> "Stateful DAG with typed state and conditional routing. The entire pipeline shares one `FulfillmentState` TypedDict — every agent reads from and writes to the same object. That's what makes the audit trail coherent. You know exactly what state was at every decision point."

---

*Server: `cd gsentinel && uvicorn api:app --port 8000` · UI: http://localhost:8000*
