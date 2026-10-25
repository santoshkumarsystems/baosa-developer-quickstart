# Source requirements, acceptance criteria, and honest coverage

**Author:** Santosh Kumar · **Source:** [`ORIGINAL-REQUIREMENTS.pdf`](ORIGINAL-REQUIREMENTS.pdf), *AI Employee Leave Assistant: Requirements, SLIs, SLOs and SLA*, v1.0 draft (five pages).

The source is a **product-level draft**. Its numeric targets are *illustrative*, explicitly not industry standards. BAOSA implements one educational slice; it does **not** claim all source business requirements are met.

## The business outcome in this quickstart

**Given** a synthetic actor with an initial 40-hour unreserved balance, a fictional Monday–Friday work schedule, and a user-selected date range/daily hours, **when** the application checks policy and the employee confirms, **then** exactly one pending-approval record may be created. All fields must match upon independent read-back.

**Acceptance gates:** record exists; correct employee; correct start/end dates; exact daily hours; correct total hours; `PENDING_APPROVAL` status. Each check must pass before a success message.

## Source BR1–BR8 coverage

| Source | Draft intent | Implemented in this quickstart | Not implemented |
|---|---|---|---|
| BR1 | Correct balances and policy answers | Synthetic balance and local eligibility rules | Live balance source, general HR policy Q&A |
| BR2 | Apply/change/cancel in one conversation | **Apply only**, pending approval | Edit, cancel, general chat |
| BR3 | Approval and overlap/blackout constraints | Never approves; blocks overlap; rechecks on submission | Blackout calendar; real manager workflow |
| BR4 | Instant-feeling responses | — | Latency/TTFT measurements and targets |
| BR5 | Multi-region availability | — | Availability or regional resilience |
| BR6 | Employee/manager access control | Fixed synthetic actor; rejects mismatched actors in backend | Real authentication, roles, multi-user security |
| BR7 | Audit of every action | In-memory check/submit/create event log | Durable tamper-resistant enterprise auditing |
| BR8 | Human handoff | — | Escalation workflow |

## SLIs/SLOs/SLAs (not measured in this demo)

The source proposes illustrative **97%** policy/balance answer accuracy, **98%** action success, **≤0.1%** wrong actions, **p95 TTFT <2s**, **p95 action completion <8s**, **99.9%** availability, **100%** audit completeness, **≥80%** containment, **≥85%** CSAT, and a sample **99.5%** availability SLA. **No mock test proves these.** A real product needs representative production-like workloads and measurement.

The source specifies **zero guardrail violations and zero access violations**, with **one violation an incident**, not an error-budget expenditure. This project treats the corresponding code paths as critical negative-test gates without claiming that a small demo achieves verified production-wide zero incidents.

## Important exclusions

The source's design rules mention checking identity/role on every tool call, reading balances from the real HR source, and handing off uncertain requests. This tutorial uses only a **simulated identity context and in-memory HR adapter**; it must never be used for actual employee records. The fictional rules are educational, not a substitute for an organization's approved policy.

### Educational agent example (additional, not expanded product scope)

The goal-directed path introduces one synthetic scenario: Thursday/Friday 16h desired against a separate 12h demo balance, with a full Friday prioritized. The agent chooses among read-only balance/schedule/eligibility tools and proposes exact daily hours. Trusted policy, confirmation, and read-back verification remain in Python. This **does not** implement the original document's edit/cancel features, blackout dates, real authentication, approvals, human handoff, or product SLOs.
