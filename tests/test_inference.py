"""Tool-use adversarial tests | Author: Santosh Kumar | MIT License."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from baosa.hr import DemoHR
from baosa.inference import (BASE_URL, FakeClient, MODEL_ID, create_client,
                             explain_live_error, live_settings, run_inference)
from baosa.policy import EMPLOYEE_ID, sample_plan


def response(*, tool_name=None, args=None, content="Done", reasoning="reasoning", finish="stop"):
    """Build a synthetic model response with optional function-call metadata for adversarial tool-use tests."""
    calls = ([] if tool_name is None else
             [SimpleNamespace(id="x1", type="function",
                              function=SimpleNamespace(name=tool_name, arguments=json.dumps(args)))])
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content, tool_calls=calls,
                                reasoning_content=reasoning), finish_reason=finish)],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=11))


class ScriptedClient:
    """A minimal deterministic model client that returns predefined responses and records input messages."""
    def __init__(self, answers):
        """Initialize fixture state and expose a compatible chat-completions entry point."""
        self.answers = iter(answers)
        self.received = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        """Return the next synthetic model response and retain the supplied request for assertions."""
        self.received.append(kwargs)
        return next(self.answers)


def test_mock_is_real_tool_code_but_zero_network_client():
    """Mock mode exercises actual trusted tool and quote creation code using synthetic
    model responses; it must not load the live OpenAI client or report billable
    tokens.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    plan = sample_plan()
    with patch.dict("os.environ", {"NEBIUS_API_KEY": ""}):
        with patch.dict("sys.modules", {"openai": None}):
            result = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID, hr=hr)
    assert result.accepted and result.calls == 2
    assert result.input_tokens is None and result.output_tokens is None
    assert result.quote_id


def test_nebius_endpoint_and_model_identifiers():
    """The published default endpoint and Beam model identifier match the intended
    documented Token Factory integration.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    assert BASE_URL == "https://api.tokenfactory.nebius.com/v1"
    assert MODEL_ID == "reflection/beam"


def test_live_requires_explicit_api_key():
    """Selecting live inference without a usable NEBIUS_API_KEY raises an actionable
    configuration error before any network request.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    with patch.dict("os.environ", {"NEBIUS_API_KEY": ""}):
        with pytest.raises(RuntimeError, match="NEBIUS_API_KEY"):
            create_client("live", sample_plan())


def test_model_changed_hours_fails_closed():
    """A model cannot silently change requested leave hours when calling the trusted
    eligibility tool.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    altered = plan.to_tool_arguments()
    altered["days"][0]["hours"] = 1
    fake = ScriptedClient([response(tool_name="check_leave", args=altered)])
    hr = DemoHR()
    result = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID, hr=hr, client=fake)
    assert not result.accepted and result.error == "UNTRUSTED_ARGUMENTS"
    assert not hr._quotes


def test_model_extra_actor_field_fails_closed():
    """The model cannot add actor identity fields to an eligibility tool call to
    impersonate another employee.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    altered = plan.to_tool_arguments()
    altered["employee_id"] = "E-1002"
    fake = ScriptedClient([response(tool_name="check_leave", args=altered)])
    assert not run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID,
                             hr=DemoHR(), client=fake).accepted


def test_model_unknown_tool_fails_closed():
    """An unrecognized model-selected tool is rejected rather than treated as an
    authorized application action.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    fake = ScriptedClient([response(tool_name="approve_leave", args=plan.to_tool_arguments())])
    result = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID,
                           hr=DemoHR(), client=fake)
    assert result.error == "UNTRUSTED_ARGUMENTS"


def test_false_model_success_without_tool_is_blocked():
    """A model claim of completion without the required trusted check does not create a
    confirmed eligibility result.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = ScriptedClient([response(content="Submitted and approved, trust me!")])
    result = run_inference(mode="mock", plan=sample_plan(), actor=EMPLOYEE_ID,
                           hr=DemoHR(), client=fake)
    assert not result.accepted and result.error == "NO_VALID_CHECK"


def test_beam_reasoning_and_tool_call_id_preserved_across_turns():
    """During multi-turn tool use, preserve reasoning content and exact tool-call IDs
    required by the OpenAI-compatible conversation protocol.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    scripted = ScriptedClient([
        response(tool_name="check_leave", args=plan.to_tool_arguments(), content=""),
        response(content="Eligible, but not submitted."),
    ])
    result = run_inference(mode="live", plan=plan, actor=EMPLOYEE_ID,
                           hr=DemoHR(), client=scripted)
    assert result.accepted and result.calls == 2
    assert result.input_tokens == 20 and result.output_tokens == 22
    second_messages = scripted.received[1]["messages"]
    assert any(m.get("role") == "assistant" and m.get("reasoning_content") == "reasoning"
               for m in second_messages)
    assert any(m.get("role") == "tool" and m.get("tool_call_id") == "x1"
               for m in second_messages)
    assert all("quote_id" not in m.get("content", "") for m in second_messages
               if m["role"] == "tool")


def test_token_truncation_blocks_submission():
    """A truncated model response is incomplete and cannot authorize further leave
    submission.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    scripted = ScriptedClient([response(content="", finish="length")])
    out = run_inference(mode="mock", plan=sample_plan(), actor=EMPLOYEE_ID,
                        hr=DemoHR(), client=scripted)
    assert not out.accepted and out.error == "TRUNCATED"


def test_empty_final_answer_fails_closed():
    """A missing visible final response must not be represented as a successful
    completed workflow.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    scripted = ScriptedClient([
        response(tool_name="check_leave", args=plan.to_tool_arguments(), content=""),
        response(content=""),
    ])
    out = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID,
                        hr=DemoHR(), client=scripted)
    assert out.error == "EMPTY_ANSWER"


def test_repeated_tool_request_fails_closed():
    """Repeated or unbounded model tool requests must not bypass the capped inference
    workflow.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    scripted = ScriptedClient([
        response(tool_name="check_leave", args=plan.to_tool_arguments(), content=""),
        response(tool_name="check_leave", args=plan.to_tool_arguments(), content=""),
    ])
    out = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID,
                        hr=DemoHR(), client=scripted)
    assert out.error == "UNEXPECTED_TOOLS" and not out.accepted


def test_missing_live_key_reports_key_not_endpoint():
    """Missing key errors take precedence over endpoint checks and clearly identify the
    setting the developer must provide.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    with patch.dict("os.environ", {"NEBIUS_API_KEY": "", "NEBIUS_BASE_URL": BASE_URL}):
        try:
            live_settings()
        except RuntimeError as exc:
            message = explain_live_error(exc)
        else:
            pytest.fail("Missing key should fail closed")
    assert "NEBIUS_API_KEY is missing" in message
    assert "NEBIUS_BASE_URL is empty" not in message


def test_live_endpoint_defaults_when_not_set():
    """A valid API key with no endpoint override uses the documented Token Factory
    HTTPS base URL.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    with patch.dict("os.environ", {"NEBIUS_API_KEY": "test-key"}):
        with patch.dict("os.environ", {"NEBIUS_BASE_URL": BASE_URL}):
            assert live_settings() == ("test-key", BASE_URL)


@pytest.mark.parametrize("endpoint", ["", "not-a-url", "http://unsafe.example/v1", "https:///v1"])
def test_misconfigured_endpoint_fails_before_network(endpoint):
    """Parameterize malformed or unsafe endpoint settings and ensure configuration
    validation stops before connecting.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    with patch.dict("os.environ", {"NEBIUS_API_KEY": "test-key", "NEBIUS_BASE_URL": endpoint}):
        with pytest.raises(RuntimeError, match="NEBIUS_BASE_URL|endpoint"):
            live_settings()


@pytest.mark.parametrize("status,expected", [
    (401, "authentication"), (402, "billing"), (403, "access"),
    (404, "model"), (429, "quota"), (500, "HTTP 500"),
])
def test_http_errors_are_distinguished_without_leaking_payload(status, expected):
    """Map provider HTTP error codes to useful troubleshooting guidance without echoing
    sensitive response content.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    class ProviderError(Exception):
        """Stand-in provider exception carrying an HTTP status for safe error-classification tests."""
        status_code = status
    message = explain_live_error(ProviderError("SECRET_API_KEY=do-not-show"))
    assert expected in message
    assert "SECRET_API_KEY" not in message


def test_unexpected_provider_error_does_not_leak_details():
    """Unexpected client or provider exceptions produce safe diagnostics rather than
    exposing keys or raw payloads.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    assert "supersecret" not in explain_live_error(RuntimeError("supersecret"))


@pytest.mark.parametrize("false_reply", [
    "Great! Your leave has been APPROVED by your manager and 24 hours were deducted.",
    "Your request was submitted successfully.",
    "The leave is now booked.",
    "I have created your vacation request.",
])
def test_false_action_claim_after_valid_tool_call_blocks_submission(false_reply):
    """Even after a valid tool exchange, unsupported prose claiming completed HR
    actions cannot be treated as trusted success.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    from baosa.workflow import Preparation, complete
    plan = sample_plan()
    hr = DemoHR()
    fake = ScriptedClient([
        response(tool_name="check_leave", args=plan.to_tool_arguments(), content=""),
        response(content=false_reply),
    ])
    result = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID, hr=hr,
                           client=fake)
    assert not result.accepted
    assert result.error == "UNTRUSTED_MODEL_CLAIM"
    assert result.quote_id is None
    assert false_reply not in result.explanation
    assert not complete(hr=hr, preparation=Preparation(plan, result), actor=EMPLOYEE_ID,
                        confirmed=True).saved
    assert hr._records == {}


@pytest.mark.parametrize("safe_reply", [
    "Eligible, but not submitted.",
    "This is not approved; the manager still needs to approve it.",
    "If approved, the remaining balance would be 16 hours.",
    "The manager must approve separately.",
])
def test_accurate_nonaction_model_replies_still_pass(safe_reply):
    """Accurate explanations of eligibility or future manager approval should be
    allowed when they do not falsely claim an action occurred.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    plan = sample_plan()
    fake = ScriptedClient([
        response(tool_name="check_leave", args=plan.to_tool_arguments(), content=""),
        response(content=safe_reply),
    ])
    result = run_inference(mode="mock", plan=plan, actor=EMPLOYEE_ID,
                           hr=DemoHR(), client=fake)
    assert result.accepted
    assert result.error is None


@pytest.mark.parametrize("bad_endpoint", [
    "https://example.com:bad/v1",
    "https://example.com:99999/v1",
    "https://bad host.example/v1",
])
def test_bad_endpoint_port_or_whitespace_rejected_before_network(bad_endpoint):
    """Port ranges, malformed ports, or whitespace in an HTTPS endpoint must be
    rejected before constructing a live client.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    with patch.dict("os.environ", {"NEBIUS_API_KEY": "test-key",
                                   "NEBIUS_BASE_URL": bad_endpoint}):
        with pytest.raises(RuntimeError, match="endpoint is invalid"):
            live_settings()
