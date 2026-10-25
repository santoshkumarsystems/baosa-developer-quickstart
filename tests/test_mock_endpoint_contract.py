"""The simulated transport is an API-shape exercise, never live inference.

Author: Santosh Kumar | BAOSA developer quickstart | MIT License."""
import json

import httpx
import pytest

from baosa.mock_endpoint import SimulatedNebiusClient, SIMULATED_URL
from baosa.inference import create_client
from baosa.policy import sample_plan
from baosa.hr import DemoHR
from baosa.workflow import prepare, complete
from baosa.agent import run_agent
from baosa.policy import EMPLOYEE_ID


def test_mock_uses_non_routable_reserved_host_and_in_process_transport():
    """The simulator uses an intentionally non-routable host and httpx.MockTransport,
    guaranteeing in-process behavior instead of real network inference.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    client = SimulatedNebiusClient()
    assert SIMULATED_URL.endswith('.invalid/v1')
    assert isinstance(client.transport, httpx.MockTransport)
    assert isinstance(client.http._transport, httpx.MockTransport)
    client.close()


def test_simulated_endpoint_rejects_wrong_http_method():
    """The mock only accepts POST to the expected /v1/chat/completions API route.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    client = SimulatedNebiusClient()
    assert client.http.get('https://simulated-nebius.invalid/v1/chat/completions').status_code == 404


def test_simulated_endpoint_rejects_absent_authorization():
    """The simulated protocol requires its own harmless fixture credential; it must not
    accept missing authorization.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    client = SimulatedNebiusClient()
    request = httpx.Request('POST', SIMULATED_URL + '/chat/completions', json={'model':'reflection/beam'})
    assert client._handle(request).status_code == 401


def test_simulated_endpoint_rejects_unexpected_model():
    """The simulator refuses a model name other than its scripted expected identifier.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    client = SimulatedNebiusClient()
    result = client.http.post(SIMULATED_URL + '/chat/completions',json={'model':'wrong','tools':[],'messages':[]})
    assert result.status_code == 400


def test_simulated_endpoint_emits_tool_call_in_openai_compatible_envelope():
    """A simulated model tool call contains the expected OpenAI-compatible message,
    function name, arguments, and call identifier.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    from baosa.agent import AGENT_TOOLS
    client = SimulatedNebiusClient()
    response = client.http.post(SIMULATED_URL + '/chat/completions',json={
        'model':'reflection/beam','tools':AGENT_TOOLS,
        'messages':[{'role':'user','content':'Find an alternative'}]})
    assert response.status_code == 200
    parsed=response.json()
    assert parsed['object'] == 'chat.completion'
    assert parsed['choices'][0]['finish_reason'] == 'tool_calls'
    assert parsed['choices'][0]['message']['tool_calls'][0]['function']['name'] == 'get_leave_balance'
    assert parsed['usage']['total_tokens'] == 0


def test_mock_fixed_flow_http_roundtrips_and_verified_record():
    """The fixed demo traverses in-process HTTP request/response envelopes and still
    creates an independently verified pending record.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr = DemoHR()
    prepared=prepare(hr=hr,plan=sample_plan())
    assert prepared.model.accepted and prepared.model.calls == 2
    outcome=complete(hr=hr,preparation=prepared,actor=EMPLOYEE_ID,confirmed=True)
    assert outcome.saved and all(outcome.checks.values())


def test_mock_agent_http_roundtrips_no_submission_without_consent():
    """The agent scenario uses in-memory HTTP tool-call exchanges; a proposal alone
    must not submit HR leave.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    hr=DemoHR(starting_balance_hours=12)
    proposal=run_agent(hr=hr,mode='mock')
    assert proposal.proposed
    assert hr._records == {}
    assert proposal.tool_trace[0]['tool']=='get_leave_balance'
    assert proposal.proposed_plan.requested_hours == 12


def test_mock_mode_ignores_live_credentials(monkeypatch):
    """The mock must stay offline even when real-looking Nebius credentials are present
    in environment variables.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    monkeypatch.setenv('NEBIUS_API_KEY','test_secret_canary')
    client=create_client('mock',sample_plan())
    assert isinstance(client,SimulatedNebiusClient)
    assert 'test_secret_canary' not in json.dumps(client.calls)
    client.close()
