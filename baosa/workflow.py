"""One trusted orchestration API shared by browser, CLI, and tests.

Author: Santosh Kumar | BAOSA developer quickstart | MIT License.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hr import DemoHR, verify_saved_outcome
from .inference import InferenceResult, run_inference
from .policy import EMPLOYEE_ID, LeavePlan


@dataclass(frozen=True)
class Preparation:
    """A leave plan paired with its model-assisted validation result, before any submission."""
    plan: LeavePlan
    model: InferenceResult


@dataclass(frozen=True)
class Completion:
    """Trusted submission result, including saved record ID and independent verification checks."""
    saved: bool
    record_id: str | None
    checks: dict[str, bool]
    message: str


def prepare(*, hr: DemoHR, plan: LeavePlan, mode: str = "mock",
            actor: str = EMPLOYEE_ID, client: Any | None = None) -> Preparation:
    """Prepare one exact leave plan without writing a record.

    The fixed-workflow model/tool path produces trusted eligibility checks
    and a quote, if eligible. Explicit employee confirmation and persistence
    occur only later in ``complete``."""
    return Preparation(plan, run_inference(mode=mode, plan=plan, actor=actor,
                                           hr=hr, client=client))


def complete(*, hr: DemoHR, preparation: Preparation, actor: str,
             confirmed: bool) -> Completion:
    # No stored, validated quote means no submission — even if LLM claimed success.
    """Submit a prepared plan and independently verify its persisted result.

    Args:
        hr: Trusted fictional HR backend, not a model-supplied object.
        preparation: Exact plan plus model/tool validation outcome.
        actor: Authenticated fictional employee ID.
        confirmed: Must be the literal Boolean ``True`` to authorize a write.

    Returns:
        Completion including a six-field read-back verification, saved ID
        and precise outcome message. Manager approval is still pending.

    A model's text never establishes success; all verification comes from
    an independent backend read after the write attempt."""
    quote = preparation.model.quote_id if preparation.model.accepted else None
    result = hr.submit(actor=actor, quote_id=quote, confirmed=confirmed)
    record_id = result.get("request_id") if result.get("ok") else None
    checks = verify_saved_outcome(hr, actor=actor, plan=preparation.plan,
                                  record_id=record_id)
    success = all(checks.values())
    return Completion(success, record_id, checks,
                      "VERIFIED: leave request created and pending manager approval."
                      if success else str(result.get("reason", "Read-back verification failed.")))
