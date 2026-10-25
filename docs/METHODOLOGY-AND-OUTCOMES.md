# BAOSA methodology — outcomes before agents

**BAOSA (pronounced “BOW-suh”)** — Before Agents, Outcomes Shape Architecture\
**Author:** Santosh Kumar · [← 30-second README](../README.md)

## The central idea

**BAOSA is an outcome-first AI engineering methodology, not an agent orchestration framework.** It helps engineers decide *what business result must happen*, *how to establish that it happened*, and *which implementation should deliver it*. Frameworks, models, and inference platforms are implementation choices.

> **Principle:** Business outcomes shape architecture—not the other way around.\
> **Methodology:** Understand → Define → Choose → Enforce → Verify → Measure.\
> **Implementation:** Fixed workflow, single agent, or multi-agent system.\
> **Evidence:** Actual verified business results—not model claims.

[See the methodology and agent-freedom diagrams](DIAGRAMS.md).

## Before choosing an agent

| Question | What we establish |
|---|---|
| **Business requirements — Who? What? Why?** | Whose problem, which business rules, and what value matters? |
| **Business outcome — What?** | What result must the business actually achieve? |
| **Success criteria — How do we know?** | Which concrete results count as correct? What independent evidence is required? |
| **Implementation — How will we deliver it?** | Is a deterministic workflow sufficient, or is adaptive single-/multi-agent behavior justified? |
| **Independent verification** | Check the actual state against the criteria instead of trusting the agent's text. |

**Freedom of approach. Not freedom of authority.** If agents are selected, they choose permitted tools, their order, and alternatives. Trusted application code enforces **Policy | Permissions | Confirmation** throughout execution. [Exactly what this means in Python →](AGENT-FREEDOM-AND-BOUNDARIES.md).

## What “verified success” means

Three words have different jobs:

- **Outcome:** What actually happened.
- **Verification:** Independent evidence that it happened correctly.
- **Success:** The verified result meets *predefined* business criteria.

A refusal can be correct without fulfilling the original request. An employee decline can be respected without submitting leave. A saved `PENDING_APPROVAL` request is a successful **submission**, not manager approval. Keep *correct resolution* and *desired-request fulfillment* as **separate** business measures.

### Our Employee Leave Assistant: three valid resolutions

| Business case | Predefined acceptable resolution | Evidence the system needs |
|---|---|---|
| Request violates leave policy | Correctly refuse the request | Policy rejection; no new leave record |
| Employee declines an eligible proposal | Respect the decision | No submission without explicit confirmation |
| Employee confirms an eligible proposal | Save a pending request | Independently read back the correct employee, dates, hours, and `PENDING_APPROVAL` status |

**Failure example:** An agent says “Submitted!” but no record exists. Verification fails; **do not count a successful submission**. A safety control can work correctly while the attempted business action fails. [Walk through the demo →](DEMO.md).

## Two business metrics that matter

**1. Did we succeed? — Verified Success Rate**

$$
\text{Verified Success Rate} = \frac{\text{Verified Successful Outcomes}}{\text{Total Evaluated Requests}} \times 100\%
$$

**2. At what cost? — Cost per Verified Success**

$$
\text{Cost per Verified Success} = \frac{\text{Total System Cost}}{\text{Verified Successful Outcomes}}
$$

Define a consistent request population, time window, outcome contract, and cost boundary *before* comparing approaches. Total cost may include inference/API usage, retries, compute, orchestration, and verification. If no request meets the verified success criteria, **cost per verified success is undefined**, not $0.

**Illustration only:** Ten evaluated requests, eight verified successes, and $4 total cost yield an **80% verified success rate** and **$0.50 per verified success**. **These figures are not measured BAOSA or Nebius results.** A cheap design that violates policy is **not** an acceptable optimization.

### Business metrics before engineering metrics

**Business metrics — WHAT?** Did we deliver the intended value, correctly and at acceptable cost? **Engineering metrics — HOW?** What can we improve (latency, tokens, tool calls, GPU utilization)? Collecting them can happen in parallel, but **business outcomes have priority when deciding what to optimize**.

> **Measure WHAT matters. Understand HOW it works. Optimize without compromising the outcome.**

[Diagram and examples →](BUSINESS-AND-ENGINEERING-METRICS.md). For this first release, the project demonstrates **outcome verification**, not aggregate success-rate/cost instrumentation or GPU telemetry.

## Evidence we have, and evidence we do not

- **Implemented:** Fixed and agent-assisted example paths, trusted policy checks, actor scoping, consent, quote revalidation, and saved-record readback.
- **Offline validated:** Existing automated tests check specified code behavior and an OpenAI-compatible simulated API envelope. They do **not** measure real Beam reasoning.
- **Not measured here:** A multi-request verified success rate, all-in system cost, live-model accuracy, real provider latency, availability, or comparative architecture advantage.
- **Next evaluation when appropriate:** Use equivalent scenario sets, outcome contracts, traffic patterns, and total-cost scope to compare candidate approaches without sacrificing policy or reliability constraints.

**Keep it simple:** Define Success. Build Simply. Verify Outcomes.
