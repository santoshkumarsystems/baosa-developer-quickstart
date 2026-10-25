# Zero-tolerance controls and evaluation plan

**Author:** Santosh Kumar · BAOSA developer quickstart

## Zero tolerance is a requirement, not proof of an infallible program

The source requirements set zero tolerated policy/guardrail breaches and zero access violations. For a real organization, **a single event is an incident**. The quickstart demonstrates fail-closed checks and automated negative tests. It **does not certify zero possible bugs, production-level security, or production SLO compliance**.

## Trust boundary

```
Employee's reviewed dates + daily hours
        │
        ▼
Application preflight (trusted Python)
        │ eligible only
        ▼
Nebius Beam (or mock) ── requests check_leave ──► Python validates
        │           only exact canonical args       and issues quote
        ▼
Application shows policy decision + model explanation
        │
Employee confirms exact request (outside the model)
        │
        ▼
Trusted backend checks actor + unused quote + current policy
        │
Create PENDING_APPROVAL record (fictional, in memory)
        │
        ▼
Read back record ── verify employee, dates, hours, status
```

A model saying "approved" or "submitted" is never treated as evidence. The opaque server-side quote is not sent to the model. It can only be consumed once; the backend independently reevaluates the policy at submission time.

## Deterministic safety gates

| Threat / failure injection | Expected behavior |
|---|---|
| Per-day hours >8, zero total, invalid/missing weekday allocations | Reject through policy validator |
| Total hours >40 available | Reject for insufficient balance |
| Overlapping pending request | Reject before creation and upon submission recheck |
| Wrong actor or other employee access | Fail with synthetic authorization rejection |
| Model changes dates or daily hours | Reject tool call as untrusted arguments |
| Model requests another employee or an undeclared tool | Reject tool call |
| Model claims success without calling the tool | Block; no quote and no submission |
| No explicit employee confirmation | Block |
| Forged or reused quote | Block |
| Stored record missing or different from requested data | Do not display verified outcome |
| Stored status is `APPROVED` instead of `PENDING_APPROVAL` | Do not display verified outcome |

Run `python -m pytest -v` to see executable tests. These tests have no network dependency.

## Model evaluation is separate from policy enforcement

**Future live Beam evaluation (not run or included):** Build a diverse corpus of consented synthetic leave utterances and equivalent canonical requests, including partial-day variants, ambiguity, long context, misleading prompts and malformed tool arguments. Record tool-selection accuracy, exact-argument accuracy, explanation faithfulness, refusal/clarification quality, tokens, TTFT, completion latency and provider cost. Compare against a small model and a deterministic-only baseline. Keep the critical safety gates *non-negotiable* rather than averaging them into a quality score.

A potential **non-safety quality rubric** may score explanation clarity, concise responses, instruction following, and correct mention of manager approval. A good composite score **never overrides a failed authorization or policy gate**.

## Constraints and omissions

The fixed actor `E-1001` is **not login/authentication**. Streamlit's in-memory demo backend is **not an enterprise access-control boundary**. There is no persistent database, transaction isolation, time-off accrual, public-holiday calendar, manager routing, audit store, multi-user tenancy, incident response system, or comprehensive input adversarial testing. Do not insert real employee information.

## Untrusted final model text

The model's final text is diagnostic, not an authoritative statement of HR state.
Explicit false claims of completed actions (e.g., `"Leave has been approved"`)
are failed closed before confirmation. The lightweight phrase filter is not a
semantic truthfulness test and can neither detect every hallucination nor replace
record verification; the UI status and final success message come exclusively
from the trusted HR adapter and independent read-back checks.

## Bounded agent extension — additional trust boundary

The second demo path asks a model to pursue the employee's goal using four tools: `get_leave_balance`, `get_work_schedule`, `check_candidate`, and `propose_alternative`. The model may decide the tool order and candidate hours; the Python backend determines whether any proposed plan is eligible. `propose_alternative` only returns a proposal and internally creates a one-use quote **outside** the model context. It cannot write or approve a record. Any unexpected tool, wrong actor, malformed arguments, out-of-range hours, reduced Friday leave, policy breach, absent confirmation, or stale quote fails closed.

The agent can make bounded choices rather than following a scripted workflow, but **the Mock Mode tool sequence is itself scripted**. Testing genuine autonomous behavior requires Live Mode with a real model, multiple prompts/seeds, and separate measurement of tool selection, final proposal accuracy, latency, tokens, and cost. Neither test count nor one mock trace demonstrates a model's reasoning quality. The remaining lack of real employee authentication and a durable HR store is unchanged.
