"""Bounded model/tool loop for Nebius Beam, with a network-free mock.

Author: Santosh Kumar | BAOSA developer quickstart | MIT License.
The model cannot submit leave. It can only request a trusted eligibility check.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

from .hr import DemoHR
from .policy import EMPLOYEE_ID, LeavePlan, parse_exact_tool_arguments

BASE_URL = "https://api.tokenfactory.nebius.com/v1"
MODEL_ID = "reflection/beam"
TOOL_NAME = "check_leave"

TOOLS = [{
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Validate requested daily vacation hours against the trusted employee schedule and balance. This tool does not submit or approve leave.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "days": {
                    "type": "array", "description": "One row for each scheduled weekday in chronological order",
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {
                            "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                            "hours": {"type": "integer", "description": "Leave hours on this date (0 through 8)"},
                        }, "required": ["date", "hours"],
                    },
                },
            },
            "required": ["start_date", "end_date", "days"],
        },
    },
}]

SYSTEM = (
    "You are a demo employee leave assistant. The authenticated user and HR balance "
    "exist only in the trusted application, not in your reasoning. "
    "Call check_leave exactly once using the dates and each day's hours that the user "
    "provided. Do not modify any field or invent a balance. "
    "After receiving the tool result, explain whether the request is eligible or blocked "
    "and repeat the reason. Do not claim submission or approval: only the application "
    "can submit after employee confirmation and independently verify its record."
)


@dataclass(frozen=True)
class InferenceResult:
    """Immutable outcome of a bounded model/tool eligibility interaction.

    Model text is diagnostic only. ``accepted`` and ``quote_id`` depend on
    trusted backend checks and never imply a saved or manager-approved record."""
    mode: str
    explanation: str
    checks: tuple[dict[str, Any], ...]
    quote_id: str | None
    accepted: bool
    calls: int
    input_tokens: int | None
    output_tokens: int | None
    error: str | None = None


class FakeClient:
    """Deterministic model fixture implementing chat.completions.create.

    Produces synthetic tool-call arguments on turn one and a synthetic
    explanation on turn two; no network or model inference occurs."""
    def __init__(self, plan: LeavePlan):
        """Initialize fixture state and expose a compatible chat-completions entry point."""
        self.plan = plan
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs: Any) -> Any:
        """Return the next synthetic model response and retain the supplied request for assertions."""
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            call = SimpleNamespace(
                id="mock-call-1", type="function",
                function=SimpleNamespace(name=TOOL_NAME,
                    arguments=json.dumps(self.plan.to_tool_arguments())),
            )
            message = SimpleNamespace(content=None, reasoning_content="mock only",
                                      tool_calls=[call])
        else:
            previous = next((row for row in reversed(kwargs["messages"])
                             if row["role"] == "tool"), None)
            result = json.loads(previous["content"]) if previous else {}
            if result.get("eligible"):
                explanation = ("The HR policy check found this request eligible. "
                               "The employee must confirm it; manager approval is still required.")
            else:
                explanation = ("The HR policy check blocked this request: " +
                               str(result.get("reason", "validation not completed")))
            message = SimpleNamespace(content=explanation, reasoning_content="",
                                      tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")],
                               usage=None)



class LiveConfigurationError(RuntimeError):
    """A required Live Mode setting is missing or invalid."""


def live_settings() -> tuple[str, str]:
    """Read and validate live-mode environment configuration before networking.

    Returns:
        ``(api_key, base_url)`` used to construct the OpenAI-compatible client.

    Raises:
        LiveConfigurationError: Missing/placeholder API key or malformed URL.

    ``NEBIUS_API_KEY`` is mandatory in live mode. ``NEBIUS_BASE_URL`` defaults
    to the Token Factory HTTPS endpoint; explicitly empty overrides are errors.
    ``NEBIUS_MODEL`` is selected at request time. ``.env`` is loaded locally,
    with existing shell variables taking precedence. No request is sent here.
    """
    from dotenv import load_dotenv
    load_dotenv(override=False)
    key = (os.getenv("NEBIUS_API_KEY") or "").strip()
    if not key or key.lower() in {"replace-with-your-own-api-key", "your-api-key", "changeme"}:
        raise LiveConfigurationError(
            "Live inference is not configured: NEBIUS_API_KEY is missing. "
            "Set your Nebius API key, or select Mock Mode. No API request was sent."
        )

    endpoint = os.getenv("NEBIUS_BASE_URL", BASE_URL).strip()
    if not endpoint:
        raise LiveConfigurationError(
            "Live inference is not configured: NEBIUS_BASE_URL is empty. "
            f"Use {BASE_URL} or another valid HTTPS inference endpoint. "
            "No API request was sent."
        )
    try:
        parsed = urlsplit(endpoint)
        # Accessing .port deliberately validates malformed ports (e.g. :bad or :99999).
        # urlsplit() alone does not reject these values.
        port = parsed.port
        valid = (parsed.scheme == "https" and bool(parsed.hostname)
                 and parsed.username is None and parsed.password is None
                 and (port is None or 1 <= port <= 65535)
                 and not any(ch.isspace() for ch in endpoint)
                 and not parsed.query and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise LiveConfigurationError(
            "Live inference endpoint is invalid: NEBIUS_BASE_URL must be an "
            "HTTPS base URL such as " + BASE_URL + ". No API request was sent."
        )
    return key, endpoint


def explain_live_error(exc: Exception) -> str:
    """Produce actionable, non-secret UI errors; never echo provider payloads."""
    if isinstance(exc, LiveConfigurationError):
        return str(exc)
    status = getattr(exc, "status_code", None)
    if status == 401:
        return "Nebius authentication failed (HTTP 401). Check NEBIUS_API_KEY."
    if status == 403:
        return "Nebius denied API access (HTTP 403). Check account/model permissions."
    if status == 402:
        return "Nebius rejected the request for billing/payment reasons (HTTP 402). Check credits and billing."
    if status == 429:
        return "Nebius rate limit or usage quota reached (HTTP 429). Check account limits before retrying."
    if status == 404:
        return "Nebius endpoint or model was not found (HTTP 404). Check NEBIUS_BASE_URL and NEBIUS_MODEL."
    if status == 400:
        return "Nebius rejected the request (HTTP 400). Check model availability and request compatibility."
    if isinstance(status, int) and 500 <= status <= 599:
        return f"Nebius service returned HTTP {status}. Try again later."
    kind = type(exc).__name__
    if kind == "APITimeoutError":
        return "The Nebius request timed out. Check your network or try again later."
    if kind == "APIConnectionError":
        return "Could not connect to the Nebius endpoint. Check the URL and network connectivity."
    return ("Live inference could not complete. Check API configuration, account access "
            "and connectivity. See server logs for non-sensitive diagnostics.")


# Deliberately conservative diagnostic filter, not an LLM truthfulness verifier.
# The model is never trusted to establish that a submission or approval happened.
# Clear affirmative action claims are blocked rather than displayed to employees.
_ACTION_VERBS = re.compile(r"\b(?:approved|submitted|booked|created|deducted)\b", re.IGNORECASE)
_NEGATED_OR_HYPOTHETICAL = re.compile(
    r"\b(?:not|never|no|without|cannot|can't|wasn't|isn't|hasn't|haven't|"
    r"weren't|aren't|didn't|if|when|once|may|might|could|would|should)\b"
    r"(?:[\W_]+[\w]+){0,4}[\W_]*$", re.IGNORECASE,
)


def makes_unsupported_action_claim(text: str) -> bool:
    """Flag explicit claims of completed action in model prose.

    This cheap heuristic is defense-in-depth, not semantic verification; all
    employee-facing status comes from trusted Python/record read-back instead.
    """
    for match in _ACTION_VERBS.finditer(text):
        preceding = text[max(0, match.start() - 65):match.start()]
        # "not approved" / "if approved" / "may be submitted" are allowed.
        if _NEGATED_OR_HYPOTHETICAL.search(preceding):
            continue
        # Some model explanations use the verb when discussing policy; prefer
        # a blocked attempt over displaying an unverified completed-action claim.
        return True
    return False


def create_client(mode: str, plan: LeavePlan) -> Any:
    """Create an inference client for the explicitly selected execution mode.

    Args:
        mode: ``mock`` for in-process simulated HTTP, or ``live`` for a real
            Nebius-compatible HTTPS request. Merely setting NEBIUS_API_KEY does
            not switch modes or initiate billable inference.
        plan: Requested leave plan; accepted for interface compatibility. The
            mock endpoint uses scripted fixtures rather than model reasoning.

    Returns:
        A chat-completions compatible client for the selected mode.

    Raises:
        ValueError: The mode is not ``mock`` or ``live``.
        LiveConfigurationError: Live mode is selected without a usable key or
            valid HTTPS endpoint. Validation occurs before any network call.

    Configuration:
        NEBIUS_API_KEY (required for live), NEBIUS_BASE_URL (optional; defaults
        to Token Factory), and NEBIUS_MODEL (optional; defaults to reflection/beam).
        ``live_settings`` loads .env without overriding shell variables.
    """
    if mode == "mock":
        from .mock_endpoint import SimulatedNebiusClient
        return SimulatedNebiusClient()
    if mode != "live":
        raise ValueError("Mode must be 'mock' or 'live'.")
    key, endpoint = live_settings()
    from openai import OpenAI
    return OpenAI(api_key=key, base_url=endpoint, timeout=60.0, max_retries=0)


def run_inference(*, mode: str, plan: LeavePlan, actor: str,
                  hr: DemoHR, client: Any | None = None,
                  max_calls: int = 3) -> InferenceResult:
    """Run one bounded chat-completions eligibility conversation.

    Args:
        mode: Explicit simulated or live inference mode.
        plan: Exact employee-entered plan that the model cannot rewrite.
        actor: Trusted identity passed only to the HR backend.
        hr: Authoritative Python policy and quote owner.
        client: Optional compatible scripted client for tests.
        max_calls: Maximum permitted model responses.

    Returns:
        InferenceResult with model explanation, trusted policy checks,
        optional single-use quote, call counts, usage fields and errors.

    A model may ask the read-only check_leave tool but cannot submit.
    Reject unknown tools, changed arguments, truncation, repetitions and
    unsupported claims. Only an eligible trusted check enables the separate
    confirmation/submission workflow. Mock usage is never a billed metric."""
    if client is None:
        client = create_client(mode, plan)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": (
            "Check my requested vacation; preserve these exact values: "
            + json.dumps(plan.to_tool_arguments(), separators=(",", ":"))
            + ". Explain the authoritative tool result, then stop."
        )},
    ]
    checks: list[dict[str, Any]] = []
    quote_id: str | None = None
    accepted = False
    input_tokens = 0 if mode == "live" else None
    output_tokens = 0 if mode == "live" else None

    def outcome(text: str, *, call_count: int, error: str | None = None) -> InferenceResult:
        """Assemble the immutable result from the accumulated trusted checks and model-call state."""
        return InferenceResult(mode, text, tuple(checks), quote_id if accepted and not error else None,
                               accepted and not error, call_count, input_tokens, output_tokens, error)

    for idx in range(max_calls):
        response = client.chat.completions.create(
            model=os.getenv("NEBIUS_MODEL", MODEL_ID) if mode == "live" else MODEL_ID,
            messages=messages, tools=TOOLS, max_tokens=4096,
            extra_body={"reasoning_effort": "low"},
        )
        usage = getattr(response, "usage", None)
        if mode == "live" and usage is not None:
            input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        if not getattr(response, "choices", None):
            return outcome("No model response.", call_count=idx + 1, error="NO_RESPONSE")
        choice = response.choices[0]
        if getattr(choice, "finish_reason", "") == "length":
            return outcome("The model reached its output-token limit.",
                           call_count=idx + 1, error="TRUNCATED")
        message = choice.message
        calls = list(getattr(message, "tool_calls", None) or [])
        content = getattr(message, "content", None) or ""
        assistant: dict[str, Any] = {"role": "assistant", "content": content}
        # Beam cookbook: preserve this history for subsequent tool-call turns.
        reasoning = getattr(message, "reasoning_content", None)
        if reasoning is not None:
            assistant["reasoning_content"] = reasoning
        if calls:
            assistant["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in calls
            ]
        messages.append(assistant)

        if not calls:
            if not checks or not accepted:
                return outcome(content or "No trusted, eligible tool check was completed.",
                               call_count=idx + 1, error="NO_VALID_CHECK")
            if not content.strip():
                return outcome("No visible model explanation was returned.",
                               call_count=idx + 1, error="EMPTY_ANSWER")
            if makes_unsupported_action_claim(content):
                # Do not display the untrusted approval/submission assertion.
                # Even a valid check does not constitute submission or approval.
                return outcome("Model response claimed an action that the application "
                               "has not performed. No submission is permitted.",
                               call_count=idx + 1, error="UNTRUSTED_MODEL_CLAIM")
            return outcome(content, call_count=idx + 1)

        # One eligible policy check per attempt; unexpected/repeated calls fail closed.
        if len(calls) != 1 or checks:
            return outcome("Model requested unexpected additional tools.",
                           call_count=idx + 1, error="UNEXPECTED_TOOLS")
        call = calls[0]
        try:
            raw = json.loads(call.function.arguments)
        except (ValueError, TypeError):
            raw = None
        if call.function.name != TOOL_NAME or not parse_exact_tool_arguments(raw, plan):
            result = {"eligible": False, "reason_code": "UNTRUSTED_ARGUMENTS",
                      "reason": "Model tool request did not exactly match employee intent."}
            checks.append(result)
            return outcome(result["reason"], call_count=idx + 1, error="UNTRUSTED_ARGUMENTS")
        # Authorization and policy are checked by trusted code, not LLM output.
        result = hr.check(actor, plan)
        checks.append(result)
        if result.get("eligible"):
            accepted = True
            quote_id = result["quote_id"]
        messages.append({"role": "tool", "tool_call_id": call.id,
                         "content": json.dumps({k: v for k, v in result.items() if k != "quote_id"})})
        # The opaque server-side quote is NEVER sent to the model.
        if not accepted:
            # Still allow one model answer explaining the rejection, never submit.
            continue
    return outcome("Model exceeded the bounded conversation length.",
                   call_count=max_calls, error="STEP_LIMIT")
