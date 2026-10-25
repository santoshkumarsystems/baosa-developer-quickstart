"""Trusted demo leave policy — never delegated to the language model.

Author: Santosh Kumar | BAOSA developer quickstart | MIT License.
This is a fictional policy and identity context, not an HR integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

EMPLOYEE_ID = "E-1001"  # Synthetic authenticated actor (NOT real authentication).
ANNUAL_ALLOWANCE_HOURS = 120  # Fictional annual entitlement, not today's balance.
STARTING_BALANCE_HOURS = 40   # Fictional remaining balance.
HOURS_PER_WORKDAY = 8
MAX_SPAN_DAYS = 14


@dataclass(frozen=True)
class DayHours:
    """One employee-selected day and its leave hours.

    ``day`` is an ISO ``YYYY-MM-DD`` date. ``hours`` is an integer candidate,
    not an authoritative approved allocation until validated by policy."""
    day: str
    hours: int


@dataclass(frozen=True)
class LeavePlan:
    """Exact employee request represented by a date range and daily hours.

    Immutable data is shared among UI, policy, tool calls, and read-back checks.
    Construction alone does not establish eligibility or authorize submission."""
    start_date: str
    end_date: str
    days: tuple[DayHours, ...]

    def to_tool_arguments(self) -> dict[str, Any]:
        """Convert a validated leave plan to the restricted model-tool argument schema."""
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "days": [{"date": item.day, "hours": item.hours} for item in self.days],
        }

    @property
    def requested_hours(self) -> int:
        """Sum the daily leave hours requested by the plan."""
        return sum(x.hours for x in self.days if type(x.hours) is int)


def working_dates(start: date, end: date) -> list[date]:
    """Return weekdays within the inclusive requested range.

    Args:
        start: First requested date.
        end: Last requested date, inclusive.

    Returns:
        Scheduled Monday–Friday dates; an empty list for invalid or overly
        large ranges. This demo intentionally does not model holidays/shifts."""
    if end < start or (end - start).days >= MAX_SPAN_DAYS:
        return []
    return [start + timedelta(days=n) for n in range((end - start).days + 1)
            if (start + timedelta(days=n)).weekday() < 5]


def plan_full_days(start: date, end: date) -> LeavePlan:
    """Construct a proposed full-day leave allocation for scheduled weekdays.

    Returns an unvalidated LeavePlan; callers must use trusted policy checks
    before issuing a quote or submitting any leave."""
    return LeavePlan(start.isoformat(), end.isoformat(),
                     tuple(DayHours(d.isoformat(), HOURS_PER_WORKDAY)
                           for d in working_dates(start, end)))


def next_monday(reference: date | None = None) -> date:
    """Return the first Monday strictly after a reference date.

    Supplying ``reference`` makes examples and date-sensitive tests
    deterministic; without it, use the machine's current date."""
    current = reference or date.today()
    return current + timedelta(days=(7 - current.weekday()) % 7 or 7)


def sample_plan(reference: date | None = None) -> LeavePlan:
    """Build the quickstart's future Monday-to-Wednesday sample request.

    This example is fictional, carries no permissions, and requires separate
    policy validation and explicit employee confirmation."""
    monday = next_monday(reference)
    return plan_full_days(monday, monday + timedelta(days=2))


def validate_plan(plan: LeavePlan, *, balance_hours: int, today: date | None = None,
                  conflicting_dates: set[str] | None = None) -> dict[str, Any]:
    """Validate the exact plan against fictional business rules; never call a model.

    Args:
        plan: Employee-requested date range and per-day hours.
        balance_hours: Available hours *after* pending reservations.
        today: Optional date used for deterministic date validation.
        conflicting_dates: Dates already reserved by pending requests.

    Returns:
        A structured eligibility result with ``eligible``, ``reason_code``,
        balances and requested hours when applicable. No records are written.

    Invariants:
        Accept only future scheduled weekdays, zero-to-eight whole hours per
        day, positive total hours, bounded ranges, and no balance/overlap
        violations. The agent's non-negotiable Friday priority is checked
        separately in ``baosa.agent.run_agent``."""
    base: dict[str, Any] = {
        "eligible": False,
        "annual_allowance_hours": ANNUAL_ALLOWANCE_HOURS,
        "available_balance_hours": balance_hours,
        "manager_approval_required": True,
    }

    def reject(code: str, message: str) -> dict[str, Any]:
        """Return a structured policy rejection rather than creating or modifying a record."""
        return {**base, "reason_code": code, "reason": message}

    try:
        start, end = date.fromisoformat(plan.start_date), date.fromisoformat(plan.end_date)
    except (ValueError, TypeError):
        return reject("INVALID_DATE", "Dates must be valid YYYY-MM-DD values.")
    if start < (today or date.today()):
        return reject("PAST_DATE", "Vacation cannot start in the past.")
    if end < start:
        return reject("DATE_ORDER", "The end date must not precede the start date.")
    if (end - start).days >= MAX_SPAN_DAYS:
        return reject("DATE_SPAN", "Choose a date range of 14 calendar days or fewer.")

    schedule = working_dates(start, end)
    if not schedule:
        return reject("NO_WORKDAYS", "The selected range contains no scheduled weekdays.")
    expected = [d.isoformat() for d in schedule]
    actual = [day.day for day in plan.days]
    if actual != expected:
        return reject("SCHEDULE_MISMATCH", "Provide one hour allocation per scheduled weekday, in order.")
    for allocation in plan.days:
        if type(allocation.hours) is not int or not 0 <= allocation.hours <= HOURS_PER_WORKDAY:
            return reject("DAILY_LIMIT", "Each scheduled day must have 0–8 whole leave hours.")
    hours = sum(day.hours for day in plan.days)
    if hours <= 0:
        return reject("ZERO_HOURS", "Choose at least one hour of vacation.")
    overlaps = (conflicting_dates or set()).intersection(
        entry.day for entry in plan.days if entry.hours > 0)
    if overlaps:
        return reject("OVERLAPPING_REQUEST", "The request overlaps an existing pending vacation request.")
    if hours > balance_hours:
        return reject("INSUFFICIENT_BALANCE",
                      f"This request needs {hours} hours; only {balance_hours} hours are available.")

    return {
        **base,
        "eligible": True,
        "reason_code": "ELIGIBLE",
        "reason": "Eligible to submit for manager approval (not approved).",
        "requested_hours": hours,
        "scheduled_hours": len(schedule) * HOURS_PER_WORKDAY,
        "remaining_if_approved": balance_hours - hours,
        "workdays": len(schedule),
    }


def parse_exact_tool_arguments(arguments: Any, expected: LeavePlan) -> bool:
    """Require model-generated tool arguments to match the original plan exactly.

    The argument keys, date strings, rows, order, and integer types must match;
    extra identity fields, Boolean-as-integer values, and changed hours fail.
    Returns a Boolean and never changes the underlying plan."""
    provided = expected.to_tool_arguments()
    if not isinstance(arguments, dict) or set(arguments) != set(provided):
        return False
    if (type(arguments.get("start_date")) is not str or
            type(arguments.get("end_date")) is not str):
        return False
    rows = arguments.get("days")
    if not isinstance(rows, list) or len(rows) != len(expected.days):
        return False
    for row, item in zip(rows, expected.days):
        if (not isinstance(row, dict) or set(row) != {"date", "hours"} or
                type(row["date"]) is not str or type(row["hours"]) is not int or
                row["date"] != item.day or row["hours"] != item.hours):
            return False
    return arguments["start_date"] == expected.start_date and arguments["end_date"] == expected.end_date
