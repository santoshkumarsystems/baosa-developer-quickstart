# Agent freedom — within three trusted walls

**Author:** Santosh Kumar · [← Methodology](METHODOLOGY-AND-OUTCOMES.md) · [Diagram](DIAGRAMS.md#2-agent-autonomy--freedom-of-approach-not-authority)

> **Give agents the freedom to decide HOW—within clearly defined boundaries.**
>
> Agents choose their permitted tools, execution order, and alternatives.
>
> **Three non-negotiable boundaries: Policy | Permissions | Confirmation.**\
> Enforced by trusted application code.

**Freedom of approach. Not freedom of authority.** BAOSA is not an orchestration framework and does not dictate a universal agent sequence. An agent can choose a useful plan **without** being able to set business policy, impersonate the employee, approve leave, or declare an unverified success.

## One concrete agent goal

An employee wants Thursday and Friday leave, with the **whole 8-hour Friday non-negotiable**. The original 16-hour plan exceeds a fictional balance of 12 hours. The goal is to **explore eligible alternatives** while preserving the employee's priority. A 4-hour Thursday plus an 8-hour Friday is *one possible* solution, not a mandatory live-model answer.

### The agent controls the HOW

The agent can choose **whether, when, and in which order** to use four permitted tools:

| Available tool | What the agent may use it for | What it does **not** do |
|---|---|---|
| `get_leave_balance` | Read available fictional leave hours | Change balance or access another employee |
| `get_work_schedule` | Read scheduled Thursday/Friday hours | Change the schedule |
| `check_candidate` | Test a candidate allocation | Override Python's eligibility decision |
| `propose_alternative` | Offer one eligible plan for employee consideration | Submit or approve leave |

These are the [actual tools exposed in `baosa/agent.py`](../baosa/agent.py). A bounded model/tool-call budget is an execution limit, **not** a prescribed order. In Mock Mode, the *fixture's* choices are scripted; real model choice is only testable after explicit Live Mode is exercised.

## Three trusted walls — exact authority

| Wall | Enforced in trusted Python | Concrete blocked case |
|---|---|---|
| **Policy** | Dates, 0–8 integer daily hours, balance, overlaps, employee's full-Friday priority | Propose only 4 Friday hours to squeeze the plan into budget |
| **Permissions** | Allowed tool list and the fictional actor's scope; no submit/approve model tool | Ask for another employee's data or request an undeclared write tool |
| **Confirmation** | Explicit Boolean confirmation of the *exact* quoted plan, checked at submission | Model proposes 12 hours and assumes approval without the employee's consent |

The implementation also **rechecks live HR state** when redeeming a single-use quote; an eligible earlier check is not an everlasting authorization. The quote remains on the **trusted side**, not in the model's messages. [Walk through the code →](CODE-WALKTHROUGH.md).

## Independent verification is separate

After valid consent and a permitted write, Python **reads the stored record back** and verifies its employee, dates, daily hours, total hours, and `PENDING_APPROVAL` status. The final status does **not** come from the model's prose. If the agent says “Submitted!” but no record exists, submission was **not verified**.

The quickstart uses a **synthetic identity and in-memory records**. It illustrates the boundaries but is not production authentication, a transactional database, or a manager-approval system.

## BAOSA is not a multi-agent requirement

Delegation, direct communication, negotiation, creator–verifier, and broadcast are *optional coordination patterns*. A deterministic workflow, one agent, or several agents can implement the methodology. Add orchestration only when the business outcome and workload justify it.

**Try it:** [Employee Leave Demo](DEMO.md) · [Run locally](RUN-LOCALLY.md) · [Optional tests](TESTING.md).
