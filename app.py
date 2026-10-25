"""BAOSA browser quickstart — Streamlit UI over trusted Python workflow.

Author: Santosh Kumar | MIT License.
Run: python -m streamlit run app.py
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

import streamlit as st

from baosa.hr import DemoHR, verify_saved_outcome
from baosa.agent import run_agent, scenario_dates
from baosa.inference import BASE_URL, MODEL_ID, explain_live_error, live_settings
from baosa.policy import (EMPLOYEE_ID, HOURS_PER_WORKDAY, DayHours,
                          LeavePlan, sample_plan, working_dates)
from baosa.workflow import Preparation, complete, prepare

st.set_page_config(page_title="BAOSA | Developer Quickstart", page_icon="🧭", layout="centered")


def reset_checked_result() -> None:
    """Clear cached eligibility results and quotes whenever a user edits the plan or changes inference mode; prevent accidental reuse of stale confirmation state."""
    for key in ("checked_fingerprint", "checked_mode", "prepared", "preflight",
                "completed", "model_problem"):
        st.session_state.pop(key, None)


def fingerprint(plan: LeavePlan) -> str:
    """Serialize the exact selected employee leave plan into a stable, sorted JSON string used to detect changes after eligibility checking."""
    return json.dumps(plan.to_tool_arguments(), sort_keys=True)


if "hr_backend" not in st.session_state:
    st.session_state.hr_backend = DemoHR()
hr: DemoHR = st.session_state.hr_backend

st.title("BAOSA")
st.caption("Before Agents, Outcomes Shape Architecture")
st.markdown("**Define Success. Build Simply. Verify Outcomes.**")
st.info("**Developer quickstart · fictional HR data.** The goal is a verified leave request awaiting manager approval—not an AI-generated success claim.")

with st.sidebar:
    st.subheader("Inference")
    mode = st.radio("Mode", ("mock", "live"),
                    format_func=lambda val: "Mock · offline and free" if val == "mock"
                    else "Live · Nebius Token Factory",
                    on_change=reset_checked_result, key="inference_mode")
    st.caption(f"Model: `{os.getenv('NEBIUS_MODEL', MODEL_ID) if mode == 'live' else MODEL_ID}`")
    st.caption("Provider: Nebius Token Factory")
    if mode == "mock":
        st.success("Synthetic model responses. No Nebius API key, network request, or inference charge.")
    else:
        try:
            live_settings()  # Check configuration only; no network request.
        except Exception as exc:
            st.warning(explain_live_error(exc))
        else:
            st.info("Live credentials and endpoint are configured, but connectivity and "
                    "credits are not verified. Real inference may incur charges.")
    with st.expander("Default Nebius API endpoint"):
        st.code(f"{BASE_URL}/chat/completions", language="text")
        st.caption("Live Mode uses this base URL unless NEBIUS_BASE_URL is explicitly overridden.")
    st.divider()
    st.caption("BAOSA is provider-agnostic; this implementation features Nebius. Not a production HR system.")

st.subheader("Choose the engineering path")
path = st.radio(
    "Path", ("structured", "agent"), horizontal=True,
    format_func=lambda value: (
        "1 · Fixed workflow — no autonomous agent" if value == "structured"
        else "2 · Goal-directed agent — bounded autonomy"),
    key="demo_path",
)
st.caption("The fixed path shows a constrained model/tool integration, not an autonomous agent. "
           "The second path lets a model choose which allowed tools to use and what alternative to propose.")

if path == "structured":
    st.subheader("1 · Define the business outcome")
    st.write("An employee requests vacation, explicitly confirms the exact hours and dates, and receives a **verified PENDING_APPROVAL** record. The AI never approves leave.")

    st.subheader("2 · Select dates and leave hours")
    original = sample_plan()
    left, right = st.columns(2)
    start = left.date_input("Start date", value=date.fromisoformat(original.start_date),
                            min_value=date.today(), key="leave_start")
    end = right.date_input("End date", value=date.fromisoformat(original.end_date),
                           min_value=date.today(), key="leave_end")

    schedule = working_dates(start, end)
    if end < start:
        st.error("End date must not precede start date.")
    elif (end - start).days >= 14:
        st.error("This quickstart supports date ranges up to 14 calendar days.")
    elif not schedule:
        st.error("This date range contains no scheduled weekdays.")

    st.caption("**Fictional policy:** 15 days (120h) annual allowance; 40h starting demo balance; Monday–Friday schedule; up to 8h leave per day. Holidays and shift calendars are outside this demo.")
    if schedule:
        st.write("**Leave hours per scheduled day** — 8 = full day, 4 = half day, 0 = no leave")
    allocations: list[DayHours] = []
    for scheduled_day in schedule:
        daily_hours = st.number_input(
            (scheduled_day.strftime("%a, %b ") + str(scheduled_day.day) + scheduled_day.strftime(", %Y")), min_value=0, max_value=HOURS_PER_WORKDAY,
            value=HOURS_PER_WORKDAY, step=1, key=f"hours_{scheduled_day.isoformat()}",
            help="0–8 whole vacation hours. The employee may request full or partial days.",
        )
        allocations.append(DayHours(scheduled_day.isoformat(), int(daily_hours)))
    plan = LeavePlan(start.isoformat(), end.isoformat(), tuple(allocations))
    col1, col2, col3 = st.columns(3)
    available_to_request = hr.balance_for(EMPLOYEE_ID)
    col1.metric("Available to request", f"{available_to_request}h")
    col2.metric("This request", f"{plan.requested_hours}h")
    col3.metric("Schedule capacity", f"{len(schedule) * HOURS_PER_WORKDAY}h")
    st.caption("New pending requests reserve hours for eligibility; the HR workflow still requires manager approval.")

    # Preflight uses the exact same trusted policy as the HR tool. In LIVE mode,
    # it avoids calling a paid model for obviously invalid requests.
    current_id = fingerprint(plan)
    previous_id = st.session_state.get("checked_fingerprint")
    request_changed = previous_id is not None and (previous_id != current_id or
                                                    st.session_state.get("checked_mode") != mode)
    if request_changed:
        st.warning("The dates or daily hours changed. Check this updated request again before submitting.")

    if st.button("Check leave eligibility", type="primary", use_container_width=True):
        reset_checked_result()
        st.session_state.checked_fingerprint = current_id
        st.session_state.checked_mode = mode
        policy = hr.evaluate(EMPLOYEE_ID, plan)
        st.session_state.preflight = policy
        if policy["eligible"]:
            try:
                with st.spinner("Calling the model and trusted leave-check tool…"):
                    st.session_state.prepared = prepare(hr=hr, plan=plan, mode=mode,
                                                        actor=EMPLOYEE_ID)
            except Exception as exc:
                # Classify known problems without leaking API keys or provider payloads.
                st.session_state.model_problem = (
                    explain_live_error(exc) if mode == "live"
                    else "The mock workflow failed unexpectedly. No request was submitted."
                )

    if not request_changed and "preflight" in st.session_state:
        st.subheader("3 · Inspect the trusted decision")
        preflight = st.session_state.preflight
        if not preflight["eligible"]:
            st.error(f"BLOCKED · {preflight['reason_code']} — {preflight['reason']}")
            st.caption("Rejected by trusted Python policy before any paid model call. No request was created.")
        elif "model_problem" in st.session_state:
            st.error(st.session_state.model_problem)
            st.caption("No leave request was submitted.")
        else:
            prepared: Preparation | None = st.session_state.get("prepared")
            if prepared:
                outcome = prepared.model
                if outcome.checks:
                    check = outcome.checks[-1]
                    if outcome.accepted and not outcome.error:
                        st.success(f"ELIGIBLE · {check['requested_hours']}h requested, "
                                   f"{check['available_balance_hours']}h available, "
                                   f"{check['remaining_if_approved']}h remaining if approved.")
                    elif outcome.error:
                        st.warning("Trusted policy check completed, but model workflow did not finish. "
                                   "No submission is allowed.")
                    else:
                        st.error(f"BLOCKED · {check.get('reason_code', 'CHECK_FAILED')} — "
                                 f"{check.get('reason', 'Unknown validation failure')}")
                    with st.expander("Trusted policy-tool result"):
                        st.json({k: v for k, v in check.items() if k != "quote_id"})
                else:
                    st.error("The model did not complete a trusted policy check.")
                with st.expander("Untrusted model reply · diagnostic only, never an HR decision"):
                    st.write(outcome.explanation or "No visible explanation")
                st.caption(f"{mode.upper()} · Model calls: {outcome.calls} · "
                           + ("Tokens: simulated / not available" if mode == "mock" else
                              f"Input/output tokens: {outcome.input_tokens}/{outcome.output_tokens}"))
                if outcome.error:
                    st.error(f"No submission allowed: {outcome.error}")

                if outcome.accepted and not outcome.error:
                    st.subheader("4 · Explicitly confirm the exact request")
                    st.write(f"**Employee {EMPLOYEE_ID}:** {plan.requested_hours}h of vacation, "
                             f"{plan.start_date} through {plan.end_date}. "
                             "The manager must approve it separately.")
                    with st.expander("Daily breakdown", expanded=False):
                        st.table([{"Date": row.day, "Vacation hours": row.hours} for row in plan.days])
                    if "completed" not in st.session_state:
                        if st.button("Confirm and submit fictional leave request", type="primary",
                                     use_container_width=True):
                            st.session_state.completed = complete(
                                hr=hr, preparation=prepared, actor=EMPLOYEE_ID, confirmed=True)
                            st.rerun()

    if not request_changed and "completed" in st.session_state:
        completed = st.session_state.completed
        st.subheader("5 · Verify the saved business outcome")
        for check_name, passed in completed.checks.items():
            st.write(("✅" if passed else "❌") + " " + check_name.replace("_", " "))
        if completed.saved:
            st.success(f"VERIFIED · {completed.record_id} · PENDING_APPROVAL (not approved)")
        else:
            st.error(completed.message)


else:
    st.subheader("1 · Give the agent an outcome, not a checklist")
    thursday, friday = scenario_dates()
    st.write(f"**Employee goal:** Take Thursday **{thursday.isoformat()}** and Friday "
             f"**{friday.isoformat()}** off, ideally 8h each. **Keep all 8h Friday** "
             "for a family event. If the balance is insufficient, find a viable alternative.")
    st.caption("**Agent freedom:** choose tools, their order, and candidate alternatives. "
               "**Trusted boundaries:** 8h Friday, selected dates only, positive eligible hours, "
               "correct employee, explicit confirmation, manager approval pending.")
    if "agent_hr_backend" not in st.session_state:
        st.session_state.agent_hr_backend = DemoHR(starting_balance_hours=12)
    agent_hr: DemoHR = st.session_state.agent_hr_backend
    st.write("**Fictional agent scenario:** 12 hours initially available; "
             "16 hours requested. This balance is independent of Scenario 1.")
    st.metric("Currently available in agent scenario", f"{agent_hr.balance_for(EMPLOYEE_ID)}h")
    st.subheader("2 · Agent explores within trusted boundaries")
    st.caption("In Mock Mode, the tool-choice trace is a scripted fixture, NOT an autonomous model decision. "
               "In Live Mode, Beam chooses tools and proposal arguments.")
    if st.button("Let the agent explore alternatives", type="primary", use_container_width=True):
        st.session_state.pop("agent_result", None)
        st.session_state.pop("agent_completion", None)
        st.session_state.agent_mode = mode
        try:
            with st.spinner("Agent using permitted read-only tools…"):
                st.session_state.agent_result = run_agent(hr=agent_hr, mode=mode,
                                                         actor=EMPLOYEE_ID)
        except Exception as exc:
            st.session_state.agent_problem = (
                explain_live_error(exc) if mode == "live"
                else "Mock agent workflow failed. No leave request was created."
            )
        else:
            st.session_state.pop("agent_problem", None)
    if "agent_problem" in st.session_state:
        st.error(st.session_state.agent_problem)
    result = st.session_state.get("agent_result")
    if result is not None and st.session_state.get("agent_mode") == mode:
        st.subheader("3 · Inspect the agent's proposed outcome")
        for index, event in enumerate(result.tool_trace, start=1):
            with st.expander(f"Tool {index}: {event['tool']}"):
                st.json(event)
        st.caption(f"{mode.upper()} · Model calls: {result.model_calls} · "
                   "Tool trace shows actions, not hidden model reasoning.")
        if result.proposed:
            proposal = result.proposed_plan
            st.success(result.summary)
            st.write("**The agent's proposal is not a submission.** Python validated the exact "
                     "daily hours, preserved Friday, and issued an opaque quote outside the model.")
            st.table([{"Date": item.day, "Leave hours": item.hours}
                      for item in proposal.days])
            st.subheader("4 · Employee confirms the proposed alternative")
            st.write(f"Employee **{EMPLOYEE_ID}**, confirm {proposal.requested_hours}h "
                     "of vacation for the displayed dates? Manager approval will still be required.")
            if "agent_completion" not in st.session_state:
                if st.button("Confirm agent proposal and submit pending request",
                             type="primary", use_container_width=True):
                    saved = agent_hr.submit(actor=EMPLOYEE_ID, quote_id=result.quote_id,
                                            confirmed=True)
                    checks = verify_saved_outcome(
                        agent_hr, actor=EMPLOYEE_ID, plan=proposal,
                        record_id=saved.get("request_id") if saved.get("ok") else None,
                    )
                    st.session_state.agent_completion = {
                        "record_id": saved.get("request_id"),
                        "checks": checks, "verified": all(checks.values()),
                        "reason": saved.get("reason", "Read-back verification failed."),
                    }
                    st.rerun()
        else:
            st.warning(f"No eligible proposal was accepted: {result.error or 'UNKNOWN'}. "
                       "No record was created.")
        if "agent_completion" in st.session_state:
            finished = st.session_state.agent_completion
            st.subheader("5 · Independently verify the saved record")
            for label, passed in finished["checks"].items():
                st.write(("✅" if passed else "❌") + " " + label.replace("_", " "))
            if finished["verified"]:
                st.success(f"VERIFIED · {finished['record_id']} · PENDING_APPROVAL (not approved)")
            else:
                st.error("Submission did not produce a verified record: " + finished["reason"])

st.divider()
st.caption("BAOSA = Before Agents, Outcomes Shape Architecture. "
           "Apply it by defining requirements, workload, outcomes, constraints, and the simplest suitable architecture. "
           "This is a developer quickstart, not a full HR or AI product. Mock mode is not a live model evaluation.")
