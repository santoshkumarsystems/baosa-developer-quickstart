# Code walkthrough — WHY the agent is free, and HOW “done” is verified

**BAOSA — Before Agents, Outcomes Shape Architecture** · Author: Santosh Kumar\
**This is an annotated developer quickstart, not a production HR system.**

Read this before trying to understand the full `tests/` directory. The story below deliberately follows **one employee outcome**, not a list of library abstractions.

## The outcome (the “WHAT”, not instructions for the agent)

The employee wants **Thursday and Friday off**, originally 8 hours each (16h), but has **12h available**. **All 8 hours of Friday are essential**. The agent is free to explore candidates for Thursday. One possible alternative is 4h Thursday + 8h Friday. That is **not a prescribed live-model answer**; other eligible Thursday allocations are permitted.

**“Done” has two stages:** (1) the agent proposes an **eligible option for the employee to consider**; (2) after a *separate explicit confirmation*, Python saves a leave request and verifies it remains `PENDING_APPROVAL`. The agent is never allowed to claim stage 2 was completed by writing a confident sentence.

| Why this step exists | Python source | Exact evidence / resulting action |
|---|---|---|
| **1. Set a goal, not a tool checklist.** The model chooses how to investigate. | [`AGENT_SYSTEM` and `AGENT_TOOLS` in `baosa/agent.py`](../baosa/agent.py) | Only four named tools exist; **submit/approve are not tools**. |
| **2. Let the agent choose.** Different permitted orders and proposals should work. | [`run_agent()`](../baosa/agent.py) | `tool_choice="auto"`; the model's actual tool calls are recorded in `tool_trace`. |
| **3. Enforce non-negotiable walls outside the prompt.** Models can propose; they cannot create policy. | [`_parse_hours()` / `run_agent()`](../baosa/agent.py), [`validate_plan()`](../baosa/policy.py) | Reject wrong actor, forbidden tool, invalid dates/daily hours, fewer than 8 Friday hours, overlaps or insufficient balance. |
| **4. Issue a quote, not a write permission for the model.** A proposal is *not* consent. | [`DemoHR.check()`](../baosa/hr.py) | A server-side, one-use quote binds the **exact eligible plan** to the actor. The quote is **not** sent to the model. |
| **5. Only the employee can authorize the write.** The model's tool trace is not a confirmation. | [`DemoHR.submit()`](../baosa/hr.py), called from [`app.py`](../app.py) | Actual Boolean `True`; correct actor; unused quote; fresh policy check; only then create `PENDING_APPROVAL`. |
| **6. Check evidence of “done”.** No success from model prose alone. | [`verify_saved_outcome()`](../baosa/hr.py) | Read back record; independently check **exists, employee, dates, daily hours, total hours, pending status**. |

## Walk one concrete request through the code

### A. Why a loop is needed only for the agent example

In [`run_agent()`](../baosa/agent.py), `tool_choice="auto"` lets the **live** model select an allowed tool and its arguments at each step. This is the *freedom* we're teaching. The model can check balance first or schedule first; it may evaluate multiple alternatives within a bounded call budget. `SimulatedNebiusClient` returns a **scripted HTTP response fixture** for that exchange—it does not autonomously decide anything.

```python
response = client.chat.completions.create(
    model=os.getenv("NEBIUS_MODEL", MODEL_ID) if mode == "live" else MODEL_ID,
    messages=messages,
    tools=AGENT_TOOLS,
    tool_choice="auto",  # The model chooses the next permitted tool.
    max_tokens=4096,
    extra_body={"reasoning_effort": "low"},
)
```

**WHY:** We specify **the outcome and available capabilities**, not a fixed sequence of tool calls. A maximum-call limit is a cost/safety boundary, **not** a hidden checklist.

### B. Why the tool choice cannot become authority

When the agent requests `check_candidate` or `propose_alternative`, Python parses and checks the proposed hours. It then calls `hr.evaluate(actor, candidate)` and rejects any proposal that does not preserve **8h Friday**. `DemoHR.evaluate()` obtains the available balance from local HR state and calls `validate_plan()`; the model never supplies the balance.

```python
policy = hr.evaluate(actor, candidate)
if hours[1] != 8:
    # Employee's full-Friday priority is enforced, not merely suggested.
    tool_response = {
        "eligible": False,
        "reason_code": "FRIDAY_PRIORITY",
        "reason": "The employee requested a full Friday; preserve 8 hours.",
    }
```

**WHY:** The agent has full freedom to explore the *HOW*, but cannot change what the employee said matters. Even a good-sounding 8h Thursday + 4h Friday suggestion must be **blocked**.

### C. Why a valid proposal does not submit leave

For a permissible candidate, `hr.check()` creates an opaque one-use quote **stored on the trusted side**. The agent gets a proposal summary; it cannot call `hr.submit()` through the tool list. The UI shows exact daily hours and asks the employee to confirm.

```python
if confirmed is not True:
    return {"ok": False, "reason": "Explicit employee confirmation is required."}
```

**WHY:** A model has no authority to consent on behalf of an employee. A string such as `"YES"` or `"false"` does not count as the actual Boolean confirmation passed by the trusted UI.

### D. Why a green model reply is not “done”

After `DemoHR.submit()` has created a pending record, `verify_saved_outcome()` calls `hr.read()` and performs **six independent comparisons** against the original confirmed plan. A success message appears **only if all checks pass**:

```python
checks = verify_saved_outcome(hr, actor=actor, plan=plan, record_id=record_id)
verified = all(checks.values())
```

**WHY:** A conversational agent could claim that leave was approved even though no record exists. The application, not the model, decides whether the business outcome occurred.

## What the original requirements PDF changes in the engineering design

The [five-page reference PDF](ORIGINAL-REQUIREMENTS.pdf) describes a **larger hypothetical product**, not implemented by this quickstart. Its BRs and service measures *motivate* the code, but this demo does not achieve or measure the draft operational targets.

| Requirement from PDF | Why it matters to our quickstart | Code or future work |
|---|---|---|
| **BR2 / BR3 — correct leave actions and approval rules** | Never save incorrect hours or silently approve leave. | `validate_plan()`, `submit()`; mock pending record. |
| **BR6 — privacy / actor access** | An agent cannot choose another employee and read their data. | Actor check in `DemoHR` (synthetic actor **only**, not real auth). |
| **BR7 — auditable actions** | We need to trace the decision and action independently of model text. | In-memory `audit` for teaching; a real product needs durable auditing. |
| **BR4 — responsive interaction** | Track user experience, not merely whether the server starts. | PDF proposes P95 TTFT <2s and P95 end-to-end action <8s. **Not measured here**. |
| **BR5 — service availability** | Meet customer commitments with engineering margin. | Draft 99.9% internal SLO vs example 99.5% external SLA; **not implemented here**. |

**Service-level vocabulary:** SLI = the measure (for example, TTFT distribution); SLO = our engineering target for that measure; SLA = an agreement with consequences. The PDF also defines zero guardrail and access violations as **incident triggers**, not an error budget. See the [complete PDF, especially pages 3–5](ORIGINAL-REQUIREMENTS.pdf#page=3) and the [SLI/SLO/SLA explanations and source-grounded examples](SERVICE-LEVELS.md).

**Optional inference measurements:** TTFT is model first-token delay; TPOT is inter-token output time; P95/P99 are percentiles of distributions, not user percentages of correctness. The original PDF supplies **no numeric P99 or TPOT goal**. We would need streaming instrumentation and real load tests to define or verify them.

## Why the tests and evals are different

**Read just these five tests first**—each is a *question about our engineering contract*:

1. `test_agent_freely_selects_different_permitted_tool_order` — are we truly allowing the model's *HOW*? (`tests/test_agent.py`)
2. `test_agent_cannot_reduce_high_priority_friday_to_fit` — can it violate an employee's non-negotiable goal? **No.**
3. `test_agent_proposal_requires_explicit_boolean_confirmation` — can a string impersonate consent? **No.**
4. `test_simulated_endpoint_emits_tool_call_in_openai_compatible_envelope` — are our simulated HTTP responses correctly shaped for tool calling? **Yes, for this fixture.**
5. `test_happy_path_creates_pending_record_and_reads_back` — did we verify the **saved record**, not a model message?

These are **offline Python tests** that simulate model outputs; they do not measure whether real Beam chooses wisely. This package contains **no `evals/` runner or live-model benchmark**. The existing `tests/` files use synthetic cases to verify policy, tool-call contracts, confirmation and saved-state readback. A future evaluation harness would need representative requests, predefined business success criteria and real provider cost measurements; live model evaluation is not claimed here.

## One sentence to take away

**Give the agent freedom over *how*, keep policy and submission authority in Python, and claim success only when independently verified business evidence says “done.”**
