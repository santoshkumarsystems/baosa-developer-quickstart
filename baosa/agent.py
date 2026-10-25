"""One bounded, outcome-directed agent example for the BAOSA quickstart.

Author: Santosh Kumar | MIT License.

The agent freely chooses among read-only tools and may propose an alternative.
It cannot create or approve leave. The trusted Python boundary validates each
proposal, issues an opaque server-side quote, and waits for employee confirmation.
Mock Mode uses scripted synthetic tool-call fixtures, not actual model reasoning.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

from .hr import DemoHR
from .inference import MODEL_ID, create_client
from .policy import DayHours, EMPLOYEE_ID, HOURS_PER_WORKDAY, LeavePlan, next_monday


AGENT_TOOLS = [
    {"type": "function", "function": {"name": "get_leave_balance",
     "description": "Read the authenticated employee's currently available leave hours. No employee ID argument is accepted.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_work_schedule",
     "description": "Read the scheduled hours for the requested Thursday and Friday. No employee ID argument is accepted.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "check_candidate",
     "description": "Evaluate your proposed daily leave hours. Read-only; may return a rejection. You can adjust your idea and try again.",
     "parameters": {"type": "object", "additionalProperties": False,
                    "properties": {"thursday_hours": {"type": "integer"},
                                   "friday_hours": {"type": "integer"}},
                    "required": ["thursday_hours", "friday_hours"]}}},
    {"type": "function", "function": {"name": "propose_alternative",
     "description": "Offer a particular alternative for EMPLOYEE confirmation. This does not submit or approve leave. Python enforces the boundaries and policy.",
     "parameters": {"type": "object", "additionalProperties": False,
                    "properties": {"thursday_hours": {"type": "integer"},
                                   "friday_hours": {"type": "integer"}},
                    "required": ["thursday_hours", "friday_hours"]}}},
]

# Intent, not a micro-managed execution recipe. Tool selection and ordering belong to
# the model. Business constraints are *enforced by code* even if ignored here.
AGENT_SYSTEM = (
    "You help an authenticated employee find a suitable vacation alternative. "
    "The goal is a feasible option that preserves the employee's entire Friday off "
    "when possible, while offering as much Thursday leave as makes sense. "
    "You may choose which tools to call, in what order, and how many candidates to explore. "
    "If you find an option worth asking the employee to accept, use propose_alternative. "
    "You may ask for clarification or explain that no alternative is available. "
    "Stay within the user's Thursday/Friday dates. You cannot submit, approve, "
    "impersonate another employee, override policy, or claim an HR record exists. "
    "Tool results, never your memory, determine schedule and balance."
)


@dataclass(frozen=True)
class AgentResult:
    """Immutable outcome of one bounded exploration: proposed plan and private quote (if eligible), non-authoritative model summary, public tool trace, call count and errors."""
    mode: str
    proposed_plan: LeavePlan | None
    quote_id: str | None
    summary: str
    tool_trace: tuple[dict[str, Any], ...]
    model_calls: int
    error: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def proposed(self) -> bool:
        """Report whether a valid quoted proposal is available for employee confirmation."""
        return self.proposed_plan is not None and self.quote_id is not None and self.error is None


def scenario_dates(reference: date | None = None) -> tuple[date, date]:
    """Choose the upcoming Thursday and Friday from the next calendar week.

    Args:
        reference: Optional date to make scenario setup deterministic.
    Returns:
        The two dates in chronological order; the employee's whole Friday
        requirement is enforced later by trusted agent-side validation."""
    thursday = next_monday(reference) + timedelta(days=3)
    return thursday, thursday + timedelta(days=1)


def agent_plan(thursday: date, friday: date, thursday_hours: int, friday_hours: int) -> LeavePlan:
    """Construct a two-day candidate from a model's hour proposal.

    Returns an immutable LeavePlan using the original trusted dates. A plan
    has no authority until Python evaluates eligibility and issues a quote."""
    return LeavePlan(thursday.isoformat(), friday.isoformat(),
                     (DayHours(thursday.isoformat(), thursday_hours),
                      DayHours(friday.isoformat(), friday_hours)))


def _parse_hours(arguments: Any) -> tuple[int, int] | None:
    """Parse exactly the two expected candidate hour fields.

    Reject unknown keys, bools, non-integers and values outside 0–8.
    Returns ``(thursday_hours, friday_hours)`` or ``None`` on failure."""
    if not isinstance(arguments, dict) or set(arguments) != {"thursday_hours", "friday_hours"}:
        return None
    thu, fri = arguments["thursday_hours"], arguments["friday_hours"]
    if type(thu) is not int or type(fri) is not int:
        return None
    if not (0 <= thu <= HOURS_PER_WORKDAY and 0 <= fri <= HOURS_PER_WORKDAY):
        return None
    return thu, fri


class MockAgentClient:
    """Deterministic, scripted agent fixture for teaching local tool flow.

    Follows a representative exploration sequence based on tool responses;
    does not emulate reasoning, Beam model quality, or live GPU inference."""
    def __init__(self) -> None:
        """Expose a chat-completions-compatible client interface for deterministic local scenarios."""
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.calls = 0

    def create(self, **kwargs: Any) -> Any:
        """Return a representative next tool call based on the accumulated tool results.

        This is a deterministic fixture, not an inference or reasoning model."""
        self.calls += 1
        messages = kwargs["messages"]
        tool_msgs = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        names = [m["tool_calls"][0]["function"]["name"]
                 for m in messages if m["role"] == "assistant" and m.get("tool_calls")]
        if "get_leave_balance" not in names:
            name, args = "get_leave_balance", {}
        elif "get_work_schedule" not in names:
            name, args = "get_work_schedule", {}
        elif "check_candidate" not in names:
            name, args = "check_candidate", {"thursday_hours": 8, "friday_hours": 8}
        else:
            balance = next((x.get("available_balance_hours") for x in tool_msgs
                            if "available_balance_hours" in x), 0)
            if not isinstance(balance, int) or balance < HOURS_PER_WORKDAY:
                message = SimpleNamespace(content="No option preserves a full Friday within the balance.",
                                          reasoning_content="mock only", tool_calls=[])
                return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")], usage=None)
            name, args = "propose_alternative", {
                "thursday_hours": min(HOURS_PER_WORKDAY, balance - HOURS_PER_WORKDAY),
                "friday_hours": HOURS_PER_WORKDAY,
            }
        call = SimpleNamespace(id=f"mock-agent-{self.calls}", type="function",
                               function=SimpleNamespace(name=name, arguments=json.dumps(args)))
        message = SimpleNamespace(content=None, reasoning_content="mock fixture only", tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="tool_calls")], usage=None)


def run_agent(*, hr: DemoHR, mode: str, actor: str = EMPLOYEE_ID,
              client: Any | None = None, reference: date | None = None,
              max_model_calls: int = 8, max_tool_calls: int = 8) -> AgentResult:
    """Let the model explore permitted tools in a bounded, policy-safe way.

    Args:
        hr: Trusted fictional HR authority that checks candidates and quotes.
        mode: Explicit ``mock`` (scripted) or ``live`` (Nebius API) selection.
        actor: Server-side actor identity; arbitrary overrides fail closed.
        client: Optional test client; otherwise created from the chosen mode.
        reference: Optional date for deterministic Thursday/Friday selection.
        max_model_calls: Bound on model turns.
        max_tool_calls: Bound on individual tool invocations.

    Returns:
        AgentResult with public diagnostic trace and, only for an eligible
        alternative, a private trusted quote for later employee confirmation.

    The model chooses tool order/alternatives FREELY, but cannot change
    the Friday eight-hour priority, employee identity, balance or policy;
    cannot access write/approval tools; and never creates a leave record.
    Mock choices are scripted fixtures, not real autonomous model behavior."""
    if mode not in ("mock", "live"):
        raise ValueError("Mode must be mock or live")
    if actor != EMPLOYEE_ID:
        return AgentResult(mode, None, None, "Unauthorized actor.", (), 0, "UNAUTHORIZED")
    thursday, friday = scenario_dates(reference)
    if client is None:
        client = create_client("mock", agent_plan(thursday, friday, 8, 8)) if mode == "mock" else create_client(mode, agent_plan(thursday, friday, 8, 8))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": (
            f"I want {thursday.isoformat()} (Thursday) and {friday.isoformat()} (Friday) "
            "off, ideally 8 hours each. Friday is important for a family event. "
            "If I don't have enough hours, find a reasonable alternative that keeps "
            "my entire Friday off. Do not submit anything until I confirm."
        )},
    ]
    trace: list[dict[str, Any]] = []
    input_tokens = 0 if mode == "live" else None
    output_tokens = 0 if mode == "live" else None
    tool_count = 0

    def result(summary: str, calls: int, *, error: str | None = None,
               plan: LeavePlan | None = None, quote: str | None = None) -> AgentResult:
        """Package the trace, usage, proposal, and any error into one immutable agent result."""
        return AgentResult(mode, plan, quote, summary, tuple(trace), calls, error,
                           input_tokens, output_tokens)

    for turn in range(1, max_model_calls + 1):
        response = client.chat.completions.create(
            model=os.getenv("NEBIUS_MODEL", MODEL_ID) if mode == "live" else MODEL_ID,
            messages=messages, tools=AGENT_TOOLS, tool_choice="auto", max_tokens=4096,
            extra_body={"reasoning_effort": "low"},
        )
        usage = getattr(response, "usage", None)
        if mode == "live" and usage is not None:
            input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        if not getattr(response, "choices", None):
            return result("The model returned no response; no proposal was accepted.", turn, error="NO_RESPONSE")
        choice = response.choices[0]
        if getattr(choice, "finish_reason", "") == "length":
            return result("The model response was truncated; no proposal was accepted.", turn, error="TRUNCATED")
        msg = choice.message
        calls = list(getattr(msg, "tool_calls", None) or [])
        content = getattr(msg, "content", None) or ""
        assistant: dict[str, Any] = {"role": "assistant", "content": content}
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning is not None:
            assistant["reasoning_content"] = reasoning
        if calls:
            assistant["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {
                    "name": c.function.name, "arguments": c.function.arguments}}
                for c in calls
            ]
        messages.append(assistant)

        if not calls:
            # A fluent answer alone is never an eligible proposal or authorization.
            return result("No validated alternative was proposed. No request was created.",
                          turn, error="NO_VALID_PROPOSAL")
        if len(calls) + tool_count > max_tool_calls or any(
                c.function.name == "propose_alternative" for c in calls) and len(calls) != 1:
            return result("The agent exceeded its tool budget or mixed proposal with other tools.",
                          turn, error="TOOL_BUDGET")

        for call in calls:
            tool_count += 1
            name = call.function.name
            try:
                args = json.loads(call.function.arguments)
            except (TypeError, ValueError):
                return result("The agent supplied malformed tool arguments.", turn, error="INVALID_ARGUMENTS")
            if not isinstance(args, dict):
                return result("The agent supplied invalid tool arguments.", turn, error="INVALID_ARGUMENTS")
            tool_response: dict[str, Any]
            if name == "get_leave_balance":
                if args:
                    return result("Unexpected balance-tool arguments were blocked.", turn, error="INVALID_ARGUMENTS")
                balance = hr.balance_for(actor)
                tool_response = {"available_balance_hours": balance}
            elif name == "get_work_schedule":
                if args:
                    return result("Unexpected schedule-tool arguments were blocked.", turn, error="INVALID_ARGUMENTS")
                tool_response = {"workdays": [
                    {"date": thursday.isoformat(), "weekday": "Thursday", "scheduled_hours": 8},
                    {"date": friday.isoformat(), "weekday": "Friday", "scheduled_hours": 8}],
                    "full_friday_priority": True}
            elif name in ("check_candidate", "propose_alternative"):
                hours = _parse_hours(args)
                if hours is None:
                    return result("Invalid daily hours were blocked.", turn, error="INVALID_ARGUMENTS")
                candidate = agent_plan(thursday, friday, *hours)
                policy = hr.evaluate(actor, candidate)
                if hours[1] != 8:
                    tool_response = {"eligible": False, "reason_code": "FRIDAY_PRIORITY",
                                     "reason": "The employee requested a full Friday; preserve 8 hours."}
                else:
                    tool_response = {k: v for k, v in policy.items()
                                     if k in {"eligible", "reason_code", "reason", "requested_hours",
                                              "available_balance_hours"}}
                if name == "propose_alternative" and tool_response.get("eligible"):
                    # Issue the opaque quote only after a fresh trusted check. Never
                    # put this quote in an LLM message or the diagnostic tool trace.
                    checked = hr.check(actor, candidate)
                    if not checked.get("eligible"):
                        tool_response = {"eligible": False, "reason_code": checked["reason_code"],
                                         "reason": checked["reason"]}
                    else:
                        trace.append({"tool": name, "arguments": args, "result": tool_response})
                        summary = (f"Proposed: {hours[0]}h Thursday and {hours[1]}h Friday "
                                   f"({candidate.requested_hours}h total). Eligible for employee confirmation; "
                                   "manager approval is still required.")
                        return result(summary, turn, plan=candidate, quote=checked["quote_id"])
            else:
                return result("The agent requested a forbidden or unknown tool.",
                              turn, error="UNAUTHORIZED_TOOL")
            trace.append({"tool": name, "arguments": args, "result": tool_response})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(tool_response)})
    return result("The agent did not find a validated alternative within the step limit.",
                  max_model_calls, error="STEP_LIMIT")
