# SLI, SLO and SLA — from business requirement to engineering commitment

**Author:** Santosh Kumar · [← Documentation index](README.md)\
**Reference:** [Original five-page Employee Leave Assistant requirements (draft PDF)](ORIGINAL-REQUIREMENTS.pdf)

## First: define the business requirement

Example: Employees should be able to request leave **correctly and reliably**, without policy bypasses or exposing someone else's information. The business result and its verification come first. Service-level targets then help select a suitable implementation.

| Term | Simple meaning | Example from the original draft |
|---|---|---|
| **SLI — Indicator** | **What we measure** | P95 time to first token (TTFT), action success rate, monthly availability |
| **SLO — Objective** | **Engineering target** for that indicator | P95 TTFT **under 2 s**, action success **at least 98%**, availability **99.9% per 30 days** |
| **SLA — Agreement** | **Contractual commitment**, possibly with remedies | Illustrative **99.5% monthly availability**, with example service credits below thresholds |

A **measured SLI is not automatically an SLO**. An **SLO is not automatically a customer SLA**. Existing SLAs may be known *before* design and should constrain architecture selection from the start; “SLI → SLO → SLA” describes the conceptual refinement, not a mandatory commercial timeline.

## Concrete trace from the source document

| Business requirement | SLI to measure | Illustrative internal SLO | Illustrative SLA |
|---|---|---|---|
| BR1 — correct answers | Weekly graded answer accuracy | ≥97%; balances from HR state | **Not promised** in sample SLA |
| BR2 — correct leave actions | Action success rate | ≥98% | Not specified |
| BR4 — responsive chat | P95 TTFT / P95 end-to-end action time | <2 s / <8 s | Not specified |
| BR5 — reliable availability | Successful requests / all requests | 99.9% per 30 days | 99.5% monthly availability |
| BR6 — protect private data | Cross-user access violations | **0** | No-exposure clause proposed |
| BR7 — auditable actions | Actions with audit records / all actions | 100% | Optional in draft |

The original draft also proposes a **wrong-action rate ≤0.1%**, **containment ≥80%**, and **CSAT ≥85%**. Zero guardrail/access violations are **incident triggers**, not events to average away in an error budget.

**Illustrative agreement details, not a real offered SLA:** below 99.5% monthly availability, a sample 10% service credit; below 99%, 25%; sample severity-one response within one hour. These belong to the *fictional requirements PDF*, **not** to Nebius, BAOSA, or this repository as contractual guarantees.

## How these targets affect implementation choices

Begin with **business requirements and outcomes**, then characterize workload: number of requests, concurrency, prompt/context size, response length, tool use, acceptable action time, reliability, and budget.

Those requirements inform model evaluation and inference selection. For example, a managed shared/serverless inference API can make a small prototype economical to operate, but sustained high-volume workloads or stricter performance control may motivate dedicated capacity or self-managed serving. The best choice needs **representative measured evidence**; this educational demo does not benchmark those options.

The project does **not** instrument real provider P95 TTFT, availability, monthly service credits, or production accuracy. [Why Nebius and Beam were chosen for the example →](DECISIONS.md) · [Business-first measurement →](BUSINESS-AND-ENGINEERING-METRICS.md).
