# BAOSA engineering decisions — business outcome before technology

**Author:** Santosh Kumar · [← Methodology](METHODOLOGY-AND-OUTCOMES.md) · [Original requirements](ORIGINAL-REQUIREMENTS.pdf)

## 1. Start with the business, not a model

**Who?** A fictional employee requesting time off.\
**What?** Correctly resolve the employee's request under approved leave rules.\
**Why?** Avoid wrong hours, unauthorized actions, or a false claim of completion.

For a confirmed, eligible submission, the outcome contract requires an **independently readable** saved leave record with the correct employee, dates, per-day hours, total hours, and **`PENDING_APPROVAL`** status. Until explicit confirmation, **no record is created**. Valid policy refusals and respected employee declines have separate resolution criteria. [Outcome definitions →](METHODOLOGY-AND-OUTCOMES.md).

## 2. Why we do not start with multi-agent orchestration

The demo has one small bounded HR use case. A **fixed workflow** can handle a fully specified valid request without autonomous planning. A **single outcome-directed agent** is useful to illustrate alternative exploration where the employee wants Thursday and Friday but has only 12 hours, with Friday's full eight hours essential. Multiple collaborating agents would add moving parts without proving more business value for this scope.

BAOSA is an **engineering methodology**, not a multi-agent framework. Delegation, negotiation, and validators may be useful elsewhere, but they are **not required** here.

## 3. Why Nebius Token Factory? — choose an inference platform

Our tutorial needs **OpenAI-compatible chat completions and tool calls** without building a GPU-serving system. **Nebius Token Factory** offers managed inference via a compatible API, letting a developer focus on the employee outcome, application code, model behavior, and trusted execution controls. For initial experimentation, this avoids setting up vLLM, GPU instances, scaling, or serving observability ourselves.

**What this choice does *not* prove:** that Nebius is the cheapest or fastest provider for this workload; that managed inference and self-managed GPUs are interchangeable; or that the tutorial meets any production SLO. A future comparison would measure candidate serving options under the *same* representative workload, service constraints and total cost scope.

**Official:** [Nebius Token Factory](https://nebius.com/services/token-factory).

## 4. Why Reflection AI Beam? — choose an initial model candidate

**Reflection AI Beam**, addressed here as `reflection/beam`, is an **initial candidate** for tool use and reasoning in a model-assisted workflow. The [Nebius Beam cookbook](https://dev.nebius.com/cookbook/beam-reflection-token-factory) documents OpenAI-compatible requests, the `NEBIUS_API_KEY`/model configuration, tool-call continuation, and preserving Beam reasoning context across model turns.

**What this choice does *not* prove:** Beam is the best model for HR leave requests, the cheapest per verified successful outcome, or even necessary for the fixed workflow. We have **not executed a real Beam evaluation in the packaged offline tests**. Model choice should ultimately follow representative success, latency, reliability and cost measurements.

**Official:** [Beam cookbook](https://dev.nebius.com/cookbook/beam-reflection-token-factory) · [Nebius cookbook repository](https://github.com/nebius/token-factory-cookbook).

### Platform ≠ model ≠ methodology

| Layer | What it decides | This demo's choice |
|---|---|---|
| **BAOSA methodology** | Business outcome, success criteria, autonomy, verification | Provider-agnostic |
| **Inference platform** | How model requests are served | Nebius Token Factory (optional live integration) |
| **Model** | Which model generates/tool-calls | Reflection AI Beam initial candidate |
| **Trusted application** | Policy, permissions, consent, saved-state verification | Python, independent of model text |

## 5. Why trusted Python owns the three walls

**Fixed workflow:** The model sees a constrained `check_leave` tool interface and cannot approve or directly submit leave. **Agent path:** The model can choose from four permitted read/check/propose tools; it has **no** submit or approval tool. These are **different paths**, not contradictory tool lists.

Python checks dates, balances, overlaps and non-negotiable Friday; it scopes the actor, holds the one-use proposal quote, waits for **literal Boolean confirmation**, rechecks policy at submission, saves only pending leave, then reads it back. A model response is never proof of a business action. [Agent freedom and three walls →](AGENT-FREEDOM-AND-BOUNDARIES.md) · [Source walkthrough →](CODE-WALKTHROUGH.md).

## 6. Why Mock Mode exists; how Live Mode stays safe

The simulated endpoint returns scripted, compatible chat-completion/tool-call JSON via **in-memory HTTP**, with **no external model execution, API charges, or simulated GPU behavior**. It is useful for deterministic demos and policy tests. Live Mode is **opt-in** with the developer's own `NEBIUS_API_KEY`; simply creating `.env` cannot trigger paid inference.

See [Mock versus Live](DEMO.md) · [Local setup](RUN-LOCALLY.md) · [Live operator checklist](LIVE-MODE-CHECKLIST.md).

## 7. Evaluation and service levels: evidence before claims

The draft [SLI/SLO/SLA guide](SERVICE-LEVELS.md) gives **illustrative targets**, not measured performance. We need a representative leave-request dataset and predefined verification contracts before claiming one model, platform or architecture has a better success rate or lower cost per verified outcome.

The current repository has **offline code tests**, not such a benchmark. [What's implemented and missing →](REQUIREMENTS-AND-COVERAGE.md) · [Honest evaluation limits →](SECURITY-AND-EVALUATION.md).
