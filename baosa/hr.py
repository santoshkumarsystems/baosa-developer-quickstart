"""In-memory fictional HR adapter; trusted checks and independent read-back.

Author: Santosh Kumar | BAOSA developer quickstart | MIT License.
Not durable storage, real authentication, payroll, or manager approval.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any
from uuid import uuid4

from .policy import (EMPLOYEE_ID, STARTING_BALANCE_HOURS, LeavePlan, validate_plan)


class DemoHR:
    """Trusted in-memory HR boundary for fictional employee leave.

    Owns the account balance, pending reservations, validation quotes, audit
    entries, and saved records. Model code can request allowed reads/checks
    but cannot mutate ``_records`` by itself. Not persistent, authenticated
    production HR storage or an approval workflow."""
    def __init__(self, *, starting_balance_hours: int = STARTING_BALANCE_HOURS) -> None:
        """Initialize one independent fictional scenario.

    Args:
        starting_balance_hours: Available hours before pending reservations.
            Only a nonnegative Python integer is accepted.

    Separate instances keep the fixed-workflow 40-hour and agent 12-hour
    demonstrations from sharing balance or requests."""
        if type(starting_balance_hours) is not int or starting_balance_hours < 0:
            raise ValueError("Starting demo balance must be a nonnegative whole number.")
        self._starting_balance_hours = starting_balance_hours
        self._quotes: dict[str, tuple[str, LeavePlan]] = {}
        self._records: dict[str, dict[str, Any]] = {}
        self.audit: list[dict[str, str]] = []  # Demo-only in-memory event log.

    def balance_for(self, actor: str) -> int | None:
        """Read the actor's remaining leave after pending reservations.

    Args:
        actor: Server-side authenticated fictional employee ID.
    Returns:
        Nonnegative available hours; ``None`` when unauthorized.

    Manager approval has not occurred: pending requests reserve hours to
    prevent multiple submissions from spending the same balance."""
        if actor != EMPLOYEE_ID:
            return None
        # Pending requests reserve hours against new requests, without approving
        # leave or changing the fictional annual entitlement.
        reserved = sum(record["hours"] for record in self._records.values()
                       if record["employee_id"] == actor and
                       record["status"] == "PENDING_APPROVAL")
        return max(0, self._starting_balance_hours - reserved)

    def _overlaps(self, actor: str) -> set[str]:
        """Return the set of dates already held by pending leave requests.

    Only positive-hour dates for the matching employee are considered. This
    is read-only and forms part of the trusted eligibility check."""
        dates: set[str] = set()
        for record in self._records.values():
            if record["employee_id"] == actor and record["status"] == "PENDING_APPROVAL":
                dates.update(row["day"] for row in record["days"] if row["hours"] > 0)
        return dates

    def evaluate(self, actor: str, plan: LeavePlan, *, today: date | None = None) -> dict[str, Any]:
        """Read-only policy and authorization evaluation of one candidate plan.

    Args:
        actor: Trusted employee identity, not an LLM-supplied override.
        plan: Proposed date/hour allocation.
        today: Optional deterministic reference date.
    Returns:
        Structured eligibility plus reasons and balance data; no quote or
        leave record is created."""
        balance = self.balance_for(actor)
        if balance is None:
            return {"eligible": False, "reason_code": "UNAUTHORIZED",
                    "reason": "Actor is not authorized to access this employee's leave."}
        return validate_plan(plan, balance_hours=balance, today=today,
                             conflicting_dates=self._overlaps(actor))

    def check(self, actor: str, plan: LeavePlan, *, today: date | None = None) -> dict[str, Any]:
        """Check an eligible plan and issue a one-time server-side quote.

    Returns a trusted opaque ``quote_id`` only on success. The quote binds
    the plan and actor but does not imply consent or submission. The model
    should never receive or log this capability token."""
        result = self.evaluate(actor, plan, today=today)
        self.audit.append({"action": "CHECK", "actor": actor,
                           "result": result["reason_code"]})
        if result["eligible"]:
            quote_id = uuid4().hex  # Unpredictable capability, kept on trusted server side.
            self._quotes[quote_id] = (actor, plan)
            return {**result, "quote_id": quote_id}
        return result

    def submit(self, *, actor: str, quote_id: str | None,
               confirmed: bool, today: date | None = None) -> dict[str, Any]:
        """Redeem a quote only with explicit employee confirmation.

    Requirements: ``confirmed is True``, unused quote, matching actor, and
    a fresh successful balance/overlap/policy check at the instant of write.

    Returns ``ok`` plus a new request ID on success; persists only a
    ``PENDING_APPROVAL`` record, never manager approval. Rejects otherwise."""
        self.audit.append({"action": "SUBMIT_ATTEMPT", "actor": actor,
                           "result": "CONFIRMED" if confirmed is True else "NOT_CONFIRMED"})
        if confirmed is not True:
            return {"ok": False, "reason": "Explicit employee confirmation is required."}
        if not quote_id or quote_id not in self._quotes:
            return {"ok": False, "reason": "No valid, unused eligibility quote."}
        issued_actor, plan = self._quotes[quote_id]
        if issued_actor != actor or actor != EMPLOYEE_ID:
            return {"ok": False, "reason": "Unauthorized employee."}
        # Recheck *at submission time*. The quote alone is not authorization.
        reevaluation = self.evaluate(actor, plan, today=today)
        if not reevaluation["eligible"]:
            return {"ok": False, "reason": reevaluation["reason"]}
        self._quotes.pop(quote_id)  # One-time quote (prevents replay).
        record_id = f"LV-{1001 + len(self._records)}"
        self._records[record_id] = {
            "request_id": record_id, "employee_id": actor,
            "start_date": plan.start_date, "end_date": plan.end_date,
            "days": [asdict(row) for row in plan.days],
            "hours": plan.requested_hours, "status": "PENDING_APPROVAL",
        }
        self.audit.append({"action": "CREATE", "actor": actor,
                           "result": record_id})
        return {"ok": True, "request_id": record_id}

    def read(self, *, actor: str, record_id: str) -> dict[str, Any] | None:
        """Read a saved record through the trusted actor/ID access check.

    Returns a defensive copy or ``None`` for missing/unauthorized records.
    This read path is distinct from the model response and supports outcome
    verification without trusting the model's explanation."""
        record = self._records.get(record_id)
        if record is None or record["employee_id"] != actor:
            return None
        return {**record, "days": [dict(row) for row in record["days"]]}


def verify_saved_outcome(hr: DemoHR, *, actor: str, plan: LeavePlan,
                         record_id: str | None) -> dict[str, bool]:
    """Independently read back and validate six persisted-record properties.

    Checks: existence, employee identity, date range, daily hour breakdown,
    total hours, and ``PENDING_APPROVAL`` status. All checks must pass for
    a verified submitted outcome. ``None``/unknown IDs fail each check.
    This is not proof of manager approval or production database durability."""
    record = hr.read(actor=actor, record_id=record_id or "")
    return {
        "record_exists": record is not None,
        "employee_matches": record is not None and record["employee_id"] == actor,
        "dates_match": record is not None and (record["start_date"], record["end_date"]) ==
        (plan.start_date, plan.end_date),
        "daily_hours_match": record is not None and record["days"] ==
        [asdict(row) for row in plan.days],
        "total_hours_match": record is not None and record["hours"] == plan.requested_hours,
        "pending_manager_approval": record is not None and record["status"] == "PENDING_APPROVAL",
    }
