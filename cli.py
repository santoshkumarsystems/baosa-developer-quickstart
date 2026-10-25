"""Command-line entry point for the same BAOSA policy and workflow.

Author: Santosh Kumar | MIT License.
"""
from __future__ import annotations

import argparse

from baosa.hr import DemoHR
from baosa.inference import MODEL_ID, explain_live_error
from baosa.policy import EMPLOYEE_ID, sample_plan
from baosa.workflow import complete, prepare


def main() -> int:
    """Execute the developer-facing fixed-workflow CLI. Default to the network-free mock; require an explicit mode for live inference and an explicit user YES/--yes before creating and verifying a fictional pending record."""
    parser = argparse.ArgumentParser(description="BAOSA leave-request developer quickstart")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--yes", action="store_true",
                        help="Explicitly authorize creation of the fictional pending request")
    args = parser.parse_args()
    plan = sample_plan()
    hr = DemoHR()
    print("BAOSA | Before Agents, Outcomes Shape Architecture")
    print(f"Inference: {args.mode.upper()} | model: {MODEL_ID}")
    if args.mode == "mock":
        print("MOCK: synthetic model replies; zero API traffic and inference charges.")
    print(f"Goal: {plan.requested_hours}h vacation, {plan.start_date} through {plan.end_date}.")
    preflight = hr.evaluate(EMPLOYEE_ID, plan)
    if not preflight["eligible"]:
        print("BLOCKED:", preflight["reason"])
        return 1
    try:
        prepared = prepare(hr=hr, plan=plan, mode=args.mode, actor=EMPLOYEE_ID)
    except Exception as exc:
        print((explain_live_error(exc) if args.mode == "live"
               else "The local mock workflow failed unexpectedly. No request was created."))
        return 1
    print("Model explanation:", prepared.model.explanation)
    print("Trusted validation:", "ELIGIBLE" if prepared.model.accepted else "BLOCKED")
    if not prepared.model.accepted:
        print("No submission permitted:", prepared.model.error or "Not validated")
        return 1
    if args.yes:
        confirmed = True
    else:
        confirmed = input("Type YES to submit this fictional request: ").strip() == "YES"
    result = complete(hr=hr, preparation=prepared, actor=EMPLOYEE_ID, confirmed=confirmed)
    for name, passed in result.checks.items():
        print(("PASS" if passed else "FAIL"), name)
    print((f"VERIFIED · {result.record_id} · PENDING_APPROVAL (not approved)"
           if result.saved else "NOT COMPLETED · " + result.message))
    return 0 if result.saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
