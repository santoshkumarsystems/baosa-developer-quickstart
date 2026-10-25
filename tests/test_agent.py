"""Executable safety and autonomy-boundary tests for the agent demo.
Author: Santosh Kumar | MIT License.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from baosa.agent import MockAgentClient, run_agent, scenario_dates
from baosa.hr import DemoHR, verify_saved_outcome
from baosa.policy import EMPLOYEE_ID


def scripted(*steps):
    """Simulate model-chosen tool order/arguments; no real inference requests."""
    class Scripted:
        """Test-only fixture implementing the subset of the inference client interface used by this suite."""
        def __init__(self):
            """Initialize fixture state and expose a compatible chat-completions entry point."""
            self.index = 0
            self.messages = []
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            """Return the next synthetic model response and retain the supplied request for assertions."""
            self.messages.append(kwargs["messages"])
            if self.index >= len(steps):
                step = None
            else:
                step = steps[self.index]
            self.index += 1
            if step is None:
                msg = SimpleNamespace(content="I submitted and approved leave!",
                                      reasoning_content="fake", tool_calls=[])
                reason = "stop"
            else:
                if isinstance(step, list):
                    calls = [SimpleNamespace(id=f"test-{self.index}-{i}", type="function",
                             function=SimpleNamespace(name=tool, arguments=json.dumps(args)))
                             for i, (tool, args) in enumerate(step)]
                else:
                    name, args = step
                    calls = [SimpleNamespace(id=f"test-{self.index}", type="function",
                                         function=SimpleNamespace(name=name, arguments=json.dumps(args)))]
                msg = SimpleNamespace(content="", reasoning_content="fake", tool_calls=calls)
                reason = "tool_calls"
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=reason)],
                                   usage=None)
    return Scripted()


def test_agent_mock_can_propose_but_cannot_submit():
    """The scripted agent can propose a 4h Thursday + 8h Friday option within 12h, but
    cannot itself create the HR record. Inspect tool trace and mock usage.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    answer = run_agent(hr=hr, mode="mock")
    assert answer.proposed
    assert [(d.hours) for d in answer.proposed_plan.days] == [4, 8]
    assert [step["tool"] for step in answer.tool_trace] == [
        "get_leave_balance", "get_work_schedule", "check_candidate", "propose_alternative"]
    assert hr._records == {}
    assert answer.model_calls == 4
    assert answer.input_tokens is None  # mock usage is not metered inference


def test_agent_proposal_requires_explicit_boolean_confirmation():
    """Even a valid agent proposal and quote cannot submit without literal True. Reject
    string/number/None consent and verify the authorized submission separately.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    answer = run_agent(hr=hr, mode="mock")
    for falsy_but_truthy in ["false", "YES", 1, None]:
        saved = hr.submit(actor=EMPLOYEE_ID, quote_id=answer.quote_id,
                          confirmed=falsy_but_truthy)
        assert saved["ok"] is False
        assert hr.audit[-1]["result"] == "NOT_CONFIRMED"
    assert not hr._records
    saved = hr.submit(actor=EMPLOYEE_ID, quote_id=answer.quote_id, confirmed=True)
    assert saved["ok"] is True
    checks = verify_saved_outcome(hr, actor=EMPLOYEE_ID,
                                  plan=answer.proposed_plan, record_id=saved["request_id"])
    assert all(checks.values())
    assert hr._records[saved["request_id"]]["status"] == "PENDING_APPROVAL"


def test_agent_freely_selects_different_permitted_tool_order():
    """Different sequences of permitted read/check tools lead to an eligible result.
    Protect agent freedom rather than requiring one hardcoded tool order.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    bot = scripted(("get_work_schedule", {}),
                   ("check_candidate", {"thursday_hours": 4, "friday_hours": 8}),
                   ("get_leave_balance", {}),
                   ("propose_alternative", {"thursday_hours": 4, "friday_hours": 8}))
    out = run_agent(hr=hr, mode="live", client=bot)
    assert out.proposed and out.model_calls == 4
    assert out.proposed_plan.requested_hours == 12
    # Each tool result was included as a matching tool-call reply in the conversation.
    final_messages = bot.messages[-1]
    tool_responses = [m for m in final_messages if m["role"] == "tool"]
    assert len(tool_responses) == 3
    assert all(m["tool_call_id"].startswith("test-") for m in tool_responses)
    assert all("reasoning_content" in m for m in final_messages if m["role"] == "assistant")


def test_agent_can_choose_different_eligible_plan_not_hardcoded():
    """The agent may propose another policy-compliant combination, not only the mock
    example of 4h Thursday plus 8h Friday.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    out = run_agent(hr=hr, mode="live", client=scripted(
        ("propose_alternative", {"thursday_hours": 2, "friday_hours": 8})))
    assert out.proposed and out.proposed_plan.requested_hours == 10
    assert not hr._records


def test_agent_cannot_reduce_high_priority_friday_to_fit():
    """An agent must never reduce the non-negotiable eight-hour Friday requirement
    merely to satisfy the remaining balance.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    out = run_agent(hr=hr, mode="live", client=scripted(
        ("propose_alternative", {"thursday_hours": 8, "friday_hours": 4})))
    assert not out.proposed
    assert out.error == "NO_VALID_PROPOSAL"
    assert out.tool_trace[0]["result"]["reason_code"] == "FRIDAY_PRIORITY"
    assert not hr._quotes and not hr._records


def test_agent_cannot_propose_more_than_balance():
    """A candidate exceeding the authoritative remaining balance must be rejected even
    when model tool arguments appear well-formed.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    out = run_agent(hr=hr, mode="live", client=scripted(
        ("propose_alternative", {"thursday_hours": 8, "friday_hours": 8})))
    assert out.error == "NO_VALID_PROPOSAL"
    assert out.tool_trace[0]["result"]["reason_code"] == "INSUFFICIENT_BALANCE"
    assert not hr._quotes and not hr._records


def test_no_model_text_can_create_or_approve_leave():
    """Text claiming leave was submitted or manager-approved does not mutate trusted HR
    state or satisfy verification.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    out = run_agent(hr=hr, mode="live", client=scripted(None))
    assert out.error == "NO_VALID_PROPOSAL" and not out.proposed
    assert not hr._quotes and not hr._records


def test_agent_cannot_invoke_write_or_approval_tools():
    """Only explicitly permitted read/check/proposal tools are exposed; agent attempts
    to write or approve records must fail.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    for tool in ("submit_leave", "approve_leave", "cancel_leave"):
        hr = DemoHR(starting_balance_hours=12)
        out = run_agent(hr=hr, mode="live", client=scripted((tool, {})))
        assert out.error == "UNAUTHORIZED_TOOL" and not hr._records


def test_agent_rejects_non_integer_hours_and_identity_override():
    """Reject invalid numeric types and identity-override fields before using
    model-supplied tool arguments.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    for args in [
        {"thursday_hours": "4", "friday_hours": 8},
        {"thursday_hours": True, "friday_hours": 8},
        {"thursday_hours": 4, "friday_hours": 8, "employee_id": "E-1002"},
        {"thursday_hours": 4, "friday_hours": 8, "start_date": "2099-01-01"},
        {"thursday_hours": -1, "friday_hours": 8},
        {"thursday_hours": 4.5, "friday_hours": 8},
    ]:
        hr = DemoHR(starting_balance_hours=12)
        out = run_agent(hr=hr, mode="live", client=scripted(("propose_alternative", args)))
        assert out.error == "INVALID_ARGUMENTS" and not hr._records and not hr._quotes


def test_agent_cannot_impersonate_another_actor():
    """A model invocation on behalf of an unauthorized actor must be denied before any
    HR action.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    bot = scripted(("get_leave_balance", {}))
    out = run_agent(hr=hr, mode="live", client=bot, actor="E-1002")
    assert out.error == "UNAUTHORIZED" and bot.index == 0


def test_agent_no_solution_when_full_friday_unaffordable():
    """If remaining balance cannot cover Friday’s required eight hours, the agent must
    not propose a supposedly valid plan.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=7)
    out = run_agent(hr=hr, mode="mock")
    assert not out.proposed and out.error == "NO_VALID_PROPOSAL"
    assert not hr._records and not hr._quotes


def test_agent_proposal_invalidated_by_later_balance_reservation():
    """A quote issued for an agent proposal is not permanent authority; later
    reservations must invalidate submission eligibility.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    first = run_agent(hr=hr, mode="mock")
    second = run_agent(hr=hr, mode="mock")
    assert first.proposed and second.proposed  # neither quote is itself a submission
    saved = hr.submit(actor=EMPLOYEE_ID, quote_id=second.quote_id, confirmed=True)
    assert saved["ok"]
    stale = hr.submit(actor=EMPLOYEE_ID, quote_id=first.quote_id, confirmed=True)
    assert stale["ok"] is False  # re-evaluation protects against stale balance/overlap
    assert len(hr._records) == 1


def test_agent_quote_is_not_sent_back_to_model_or_tool_trace():
    """The opaque trusted submission quote must remain on the server, not in messages
    sent to the model or in diagnostic traces.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    bot = scripted(("propose_alternative", {"thursday_hours": 4, "friday_hours": 8}))
    out = run_agent(hr=hr, mode="live", client=bot)
    assert out.proposed and out.quote_id
    assert out.quote_id not in json.dumps(out.tool_trace)
    assert out.quote_id not in json.dumps(bot.messages)


def test_agent_enforces_call_limit_and_rejects_mixed_proposals():
    """The orchestrator bounds tool/model calls and refuses to mix a final proposal
    with unrelated tools in one turn.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR(starting_balance_hours=12)
    bot = scripted(*[("get_leave_balance", {})] * 10)
    out = run_agent(hr=hr, mode="live", client=bot, max_model_calls=3, max_tool_calls=3)
    assert out.error == "STEP_LIMIT" and not out.proposed
    out2 = run_agent(hr=hr, mode="live", client=scripted([
        ("propose_alternative", {"thursday_hours": 4, "friday_hours": 8}),
        ("get_leave_balance", {}),
    ]))
    assert out2.error == "TOOL_BUDGET"
    assert not hr._quotes and not hr._records


def test_agent_balance_is_scenario_specific():
    """The agent’s 12-hour fictional balance must be separate from the fixed-workflow
    scenario’s 40-hour balance.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    assert DemoHR().balance_for(EMPLOYEE_ID) == 40
    assert DemoHR(starting_balance_hours=12).balance_for(EMPLOYEE_ID) == 12
