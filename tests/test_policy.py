"""Policy contract tests | Author: Santosh Kumar | MIT License."""
from datetime import date, timedelta

from baosa.policy import (ANNUAL_ALLOWANCE_HOURS, DayHours, LeavePlan,
                          next_monday, plan_full_days, sample_plan,
                          validate_plan, parse_exact_tool_arguments)


def monday() -> date:
    """Return a future Monday so date-sensitive cases do not depend on today’s weekday."""
    return next_monday()


def plan(workdays: int = 3) -> LeavePlan:
    """Build a representative full-day leave plan over the requested number of weekdays."""
    m = monday()
    return plan_full_days(m, m + timedelta(days=workdays - 1))


def test_full_day_three_days_is_24_hours():
    """Three scheduled eight-hour days are eligible against 40 available hours. Assert
    the 24-hour total, 16-hour remainder, and distinction between annual
    allowance and current balance.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    response = validate_plan(plan(), balance_hours=40)
    assert response["eligible"] and response["requested_hours"] == 24
    assert response["remaining_if_approved"] == 16
    assert response["annual_allowance_hours"] == ANNUAL_ALLOWANCE_HOURS == 120


def test_partial_day_is_allowed():
    """A four-hour final day is valid in a three-day plan. Assert that partial leave
    totals 20 hours without violating the full-day maximum.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    partial = LeavePlan(p.start_date, p.end_date, p.days[:-1] + (DayHours(p.days[-1].day, 4),))
    result = validate_plan(partial, balance_hours=40)
    assert result["eligible"] and result["requested_hours"] == 20


def test_one_hour_is_allowed():
    """One hour of vacation on each of three workdays is permitted. Assert that the
    exact total is three hours.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    one = LeavePlan(p.start_date, p.end_date, tuple(DayHours(r.day, 1) for r in p.days))
    assert validate_plan(one, balance_hours=40)["requested_hours"] == 3


def test_32_hours_over_three_days_is_rejected():
    """A single 16-hour day is invalid even if the total balance could cover the plan.
    Assert the trusted DAILY_LIMIT policy rejection.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    bad = LeavePlan(p.start_date, p.end_date, p.days[:-1] + (DayHours(p.days[-1].day, 16),))
    assert validate_plan(bad, balance_hours=40)["reason_code"] == "DAILY_LIMIT"


def test_insufficient_balance_is_rejected_independently():
    """A syntactically valid plan must fail when its requested total exceeds the
    employee’s available balance. Check the insufficient-balance reason.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan_full_days(monday(), monday() + timedelta(days=6))  # Five weekdays, 40h.
    assert validate_plan(p, balance_hours=24)["reason_code"] == "INSUFFICIENT_BALANCE"


def test_zero_hours_is_rejected():
    """A plan allocating zero leave across all scheduled days does not constitute a
    valid request. Assert a trusted rejection.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    zero = LeavePlan(p.start_date, p.end_date, tuple(DayHours(r.day, 0) for r in p.days))
    assert validate_plan(zero, balance_hours=40)["reason_code"] == "ZERO_HOURS"


def test_malformed_date_is_rejected():
    """Malformed calendar dates must fail closed during policy parsing instead of
    producing a leave quote.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    assert validate_plan(LeavePlan("2026-99-99", p.end_date, p.days), balance_hours=40)["reason_code"] == "INVALID_DATE"


def test_past_dates_rejected():
    """Past start dates cannot pass leave eligibility even if the balance and hours are
    otherwise valid.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    yesterday = date.today() - timedelta(days=1)
    p = plan_full_days(yesterday, yesterday + timedelta(days=2))
    assert validate_plan(p, balance_hours=40)["reason_code"] == "PAST_DATE"


def test_inverted_dates_rejected():
    """An end date preceding the start date is invalid. Confirm validation rejects
    reversed time ranges.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    assert validate_plan(LeavePlan(p.end_date, p.start_date, p.days), balance_hours=40)["reason_code"] == "DATE_ORDER"


def test_large_span_rejected():
    """Requests exceeding the demo calendar-span limit are rejected independently of
    available leave hours.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    m = monday()
    p = LeavePlan(m.isoformat(), (m + timedelta(days=14)).isoformat(), ())
    assert validate_plan(p, balance_hours=40)["reason_code"] == "DATE_SPAN"


def test_weekends_skipped_by_schedule():
    """The demo counts scheduled Monday–Friday workdays, excluding weekends from
    requested hours.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    m = monday()
    p = plan_full_days(m, m + timedelta(days=6))
    assert len(p.days) == 5
    assert all(date.fromisoformat(row.day).weekday() < 5 for row in p.days)


def test_weekend_only_rejected():
    """A range containing no scheduled weekdays cannot create a valid leave request.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    m = monday()
    sat = m + timedelta(days=5)
    p = plan_full_days(sat, sat + timedelta(days=1))
    assert validate_plan(p, balance_hours=40)["reason_code"] == "NO_WORKDAYS"


def test_missing_workday_blocked():
    """A candidate omitting a required scheduled weekday is not an exact match for the
    requested date range.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    altered = LeavePlan(p.start_date, p.end_date, p.days[:-1])
    assert validate_plan(altered, balance_hours=40)["reason_code"] == "SCHEDULE_MISMATCH"


def test_injected_weekend_blocked():
    """A model must not invent leave hours on unscheduled weekend dates to alter
    eligibility.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    weekend = (monday() + timedelta(days=5)).isoformat()
    altered = LeavePlan(p.start_date, p.end_date, p.days + (DayHours(weekend, 8),))
    assert validate_plan(altered, balance_hours=40)["reason_code"] == "SCHEDULE_MISMATCH"


def test_boolean_hours_not_accepted():
    """Python booleans must not pass integer-hour validation despite bool being a
    subclass of int.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    altered = LeavePlan(p.start_date, p.end_date, p.days[:-1] + (DayHours(p.days[-1].day, True),))
    assert validate_plan(altered, balance_hours=40)["reason_code"] == "DAILY_LIMIT"


def test_overlapping_hours_blocked():
    """Leave already reserved by a pending record blocks a conflicting request for the
    same day.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    assert validate_plan(p, balance_hours=40,
                         conflicting_dates={p.days[1].day})["reason_code"] == "OVERLAPPING_REQUEST"


def test_model_argument_comparison_exact():
    """Model-supplied tool arguments must match the employee’s original plan exactly;
    substitutions are not trusted.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    data = p.to_tool_arguments()
    assert parse_exact_tool_arguments(data, p)
    data["days"][0]["hours"] = 4
    assert not parse_exact_tool_arguments(data, p)


def test_model_arguments_reject_extra_employee_and_bool():
    """Extra identity fields or Boolean hour values supplied by a model must be
    rejected at the schema boundary.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = plan()
    data = p.to_tool_arguments()
    data["employee_id"] = "E-1002"
    assert not parse_exact_tool_arguments(data, p)
    del data["employee_id"]
    data["days"][0]["hours"] = True
    assert not parse_exact_tool_arguments(data, p)


def test_example_uses_future_date():
    """The sample leave dates must stay in the future regardless of the day the test
    executes.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    assert date.fromisoformat(sample_plan().start_date) > date.today()


def test_56_hours_from_seven_workdays_exceeds_real_demo_balance():
    """Seven eight-hour workdays total 56 hours and must fail against the fictional
    40-hour available balance.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    m = monday()
    p = plan_full_days(m, m + timedelta(days=8))  # Mon through following Tue.
    assert len(p.days) == 7 and p.requested_hours == 56
    result = validate_plan(p, balance_hours=40)
    assert not result["eligible"]
    assert result["reason_code"] == "INSUFFICIENT_BALANCE"
    assert "40" in result["reason"]
