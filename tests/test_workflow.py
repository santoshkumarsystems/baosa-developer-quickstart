"""Negative and verified-outcome tests | Author: Santosh Kumar | MIT License."""
from datetime import timedelta

from baosa.hr import DemoHR, verify_saved_outcome
from baosa.policy import EMPLOYEE_ID, DayHours, LeavePlan, next_monday, sample_plan
from baosa.workflow import complete, prepare


def test_happy_path_creates_pending_record_and_reads_back():
    """Confirm a quoted eligible leave plan; verify the persisted request exists and
    matches the employee, dates, daily hours, total hours, and PENDING_APPROVAL
    state.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    pre = prepare(hr=hr, plan=sample_plan())
    assert pre.model.accepted and pre.model.calls == 2
    result = complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=True)
    assert result.saved and result.record_id == "LV-1001"
    assert all(result.checks.values())
    assert hr.read(actor=EMPLOYEE_ID, record_id=result.record_id)["status"] == "PENDING_APPROVAL"
    assert [event["action"] for event in hr.audit] == ["CHECK", "SUBMIT_ATTEMPT", "CREATE"]


def test_no_confirmation_prevents_creation():
    """A prepared request is not a submitted request. Confirm that withholding employee
    consent leaves the record store empty.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    pre = prepare(hr=hr, plan=sample_plan())
    result = complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=False)
    assert not result.saved and hr.read(actor=EMPLOYEE_ID, record_id="LV-1001") is None


def test_cannot_submit_without_issued_quote():
    """Direct submission without a server-issued eligibility quote must fail,
    regardless of any client claim of eligibility.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    assert not hr.submit(actor=EMPLOYEE_ID, quote_id="fake", confirmed=True)["ok"]


def test_quote_is_single_use():
    """After one authorized submission the same quote cannot be redeemed again; prevent
    replay and duplicate records.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    pre = prepare(hr=hr, plan=sample_plan())
    first = complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=True)
    second = complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=True)
    assert first.saved and not second.saved


def test_only_authenticated_actor_can_redeem_quote():
    """A quote issued for one employee must not authorize another actor to submit the
    leave request.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    pre = prepare(hr=hr, plan=sample_plan())
    result = complete(hr=hr, preparation=pre, actor="E-1002", confirmed=True)
    assert not result.saved
    assert hr.read(actor="E-1002", record_id="LV-1001") is None


def test_unauthorized_actor_cannot_check_employee():
    """An unauthenticated or mismatched actor cannot inspect employee eligibility or
    obtain a trusted quote.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    assert hr.check("E-1002", sample_plan())["reason_code"] == "UNAUTHORIZED"


def test_pending_overlap_prevents_second_record():
    """A pending request reserves its dates; a second overlapping leave submission must
    be denied.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    p = sample_plan()
    pre = prepare(hr=hr, plan=p)
    assert complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=True).saved
    assert hr.check(EMPLOYEE_ID, p)["reason_code"] == "OVERLAPPING_REQUEST"


def test_live_balance_and_overlap_are_rechecked_at_submit():
    """A previously valid quote cannot bypass changes to balance or overlapping
    reservations. Revalidate immediately before saving.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    plan = sample_plan()
    first = prepare(hr=hr, plan=plan)
    second = prepare(hr=hr, plan=plan)  # Two eligible quotes before either is used.
    assert complete(hr=hr, preparation=first, actor=EMPLOYEE_ID, confirmed=True).saved
    assert not complete(hr=hr, preparation=second, actor=EMPLOYEE_ID, confirmed=True).saved


def test_verified_success_not_inferred_from_model_text():
    """A fluent model success claim must not become a saved outcome without trusted
    persistence and read-back.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    plan = sample_plan()
    check = verify_saved_outcome(hr, actor=EMPLOYEE_ID, plan=plan, record_id="LV-FAKE")
    assert not any(check.values())


def test_record_tampering_is_detected():
    """Independent verification must detect a saved record that no longer matches the
    confirmed request.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    plan = sample_plan()
    pre = prepare(hr=hr, plan=plan)
    complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=True)
    hr._records["LV-1001"]["status"] = "APPROVED"  # Attack/fault injection in test only.
    checks = verify_saved_outcome(hr, actor=EMPLOYEE_ID, plan=plan, record_id="LV-1001")
    assert not checks["pending_manager_approval"]


def test_partial_leave_works_end_to_end():
    """A valid partial-day request moves through preparation, explicit confirmation,
    pending persistence and independent read-back.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    p = sample_plan()
    partial = LeavePlan(p.start_date, p.end_date,
                        p.days[:2] + (DayHours(p.days[2].day, 4),))
    hr = DemoHR()
    pre = prepare(hr=hr, plan=partial)
    assert pre.model.accepted
    assert pre.model.checks[-1]["requested_hours"] == 20
    assert complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID, confirmed=True).saved


def test_non_overlapping_pending_requests_still_reserve_balance():
    """Different pending date ranges still consume the same available leave balance and
    cannot be double-spent.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    first_plan = sample_plan()  # Mon-Wed, 24h.
    first = prepare(hr=hr, plan=first_plan)
    assert complete(hr=hr, preparation=first, actor=EMPLOYEE_ID, confirmed=True).saved
    assert hr.balance_for(EMPLOYEE_ID) == 16
    # Thu, Fri, next Monday: distinct days, but needs 24h > 16h available.
    start = next_monday() + timedelta(days=3)
    second_plan = LeavePlan(
        start.isoformat(), (start + timedelta(days=4)).isoformat(),
        (DayHours(start.isoformat(), 8),
         DayHours((start + timedelta(days=1)).isoformat(), 8),
         DayHours((start + timedelta(days=4)).isoformat(), 8)),
    )
    result = hr.check(EMPLOYEE_ID, second_plan)
    assert result["reason_code"] == "INSUFFICIENT_BALANCE"
    assert not result["eligible"]


def test_non_boolean_confirmation_cannot_submit():
    """Truth-like strings or numbers do not satisfy confirmed is True, and cannot
    create a leave record.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    prepared = prepare(hr=hr, plan=sample_plan())
    for value in ("false", "YES", 1, [], None):
        attempt = hr.submit(actor=EMPLOYEE_ID, quote_id=prepared.model.quote_id,
                            confirmed=value)
        assert not attempt["ok"]
    assert hr.read(actor=EMPLOYEE_ID, record_id="LV-1001") is None
    assert complete(hr=hr, preparation=prepared, actor=EMPLOYEE_ID, confirmed=True).saved


def test_non_boolean_confirmation_audit_is_truthful():
    """The audit trail must record non-Boolean confirmation attempts as NOT_CONFIRMED,
    not as authorized consent.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    pre = prepare(hr=hr, plan=sample_plan())
    for value in ("false", "YES", 1, {}, None, False):
        assert not hr.submit(actor=EMPLOYEE_ID, quote_id=pre.model.quote_id,
                             confirmed=value)["ok"]
        assert hr.audit[-1] == {
            "action": "SUBMIT_ATTEMPT", "actor": EMPLOYEE_ID,
            "result": "NOT_CONFIRMED",
        }
    assert complete(hr=hr, preparation=pre, actor=EMPLOYEE_ID,
                    confirmed=True).saved
    assert hr.audit[-2]["result"] == "CONFIRMED"
