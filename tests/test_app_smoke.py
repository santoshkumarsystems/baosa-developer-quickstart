"""Dependency-free Streamlit page smoke tests using a minimal in-process UI stub.

These tests exercise Python page orchestration, NOT Streamlit's rendered browser UI.
Author: Santosh Kumar | MIT License.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import ModuleType

import pytest


class State(dict):
    """Mapping-backed stand-in for Streamlit session_state with dot-attribute access."""
    def __getattr__(self, item):
        """Read the requested synthetic session-state attribute; raise AttributeError if it does not exist."""
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item) from None

    def __setattr__(self, key, value):
        """Write the requested session-state attribute into the test mapping."""
        self[key] = value


class Container:
    """No-op context manager supporting the subset of Streamlit layout calls used by the demo."""
    def __enter__(self):
        """Permit use of the simulated layout container in a Python with statement."""
        return self

    def __exit__(self, *_):
        """Propagate exceptions raised inside the simulated layout context."""
        return False

    def metric(self, *a, **kw):
        """Accept a metric-display call without rendering any browser elements."""
        pass

    def date_input(self, *a, **kw):
        """Return the fixture-provided date exactly as the UI’s selected date."""
        return kw['value']


class StreamlitStub(ModuleType):
    """Minimal in-process fake Streamlit module used to inspect app orchestration without launching a browser."""
    def __init__(self):
        """Initialize the fake Streamlit module, session state, scripted user choices and captured messages."""
        super().__init__('streamlit')
        self.session_state = State()
        self.sidebar = Container()
        self.click_label = None
        self.rerun_requested = False
        self.messages = []
        self.mode = 'mock'
        self.path = 'structured'

    def set_page_config(self, *a, **kw):
        """Ignore page configuration; it has no behavioral effect in these orchestration tests."""
        pass

    def radio(self, label, choices, **kw):
        """Select the scripted path or inference mode instead of waiting for user input."""
        return self.path if label == "Path" else self.mode

    def columns(self, n):
        """Provide the requested number of simulated layout containers."""
        return [Container() for _ in range(n)]

    def date_input(self, *a, **kw):
        """Return the fixture-provided date exactly as the UI’s selected date."""
        return kw['value']

    def number_input(self, label, *a, **kw):
        """Return the fixture-provided numeric input value unchanged."""
        return kw['value']

    def button(self, label, **kw):
        """Return True only for the single scripted click label; consume it after that click."""
        clicked = label == self.click_label
        if clicked:
            self.click_label = None
        return clicked

    def expander(self, *a, **kw):
        """Return a no-op context manager for expandable UI sections."""
        return Container()

    def spinner(self, *a, **kw):
        """Return a no-op context manager for progress indicators."""
        return Container()

    def rerun(self):
        """Record that the UI requested a rerun, without starting a new process."""
        self.rerun_requested = True

    def __getattr__(self, item):
        """Provide no-op Streamlit display functions while recording emitted UI messages.

        Missing interactive methods raise AttributeError rather than silently
        pretending an unsupported API action succeeded.
        """
        # Display-only Streamlit methods: retain the call signature and record output.
        if item in {'title','caption','markdown','info','success','warning','error','write',
                    'subheader','metric','code','divider','json','table'}:
            def record(*args, **kwargs):
                """Capture a simulated Streamlit output message for later assertions."""
                self.messages.append((item, args, kwargs))
            return record
        raise AttributeError(item)


APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def run_page(monkeypatch, fake: StreamlitStub):
    """Execute the app module against a chosen fake Streamlit interaction and return the resulting state."""
    monkeypatch.setitem(sys.modules, 'streamlit', fake)
    runpy.run_path(APP, run_name='__baosa_ui_smoke__')


def test_browser_initial_page_and_check_flow(monkeypatch):
    """The Streamlit orchestration renders the fixed workflow and performs a trusted
    eligibility check when the simulated user clicks the button.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    run_page(monkeypatch, fake)
    assert 'hr_backend' in fake.session_state
    assert 'prepared' not in fake.session_state
    fake.click_label = 'Check leave eligibility'
    run_page(monkeypatch, fake)
    assert fake.session_state.prepared.model.accepted
    assert fake.session_state.prepared.plan.requested_hours == 24
    fake.click_label = 'Confirm and submit fictional leave request'
    run_page(monkeypatch, fake)
    assert fake.rerun_requested
    run_page(monkeypatch, fake)
    assert fake.session_state.completed.saved
    assert fake.session_state.completed.record_id == 'LV-1001'
    assert all(fake.session_state.completed.checks.values())


def test_browser_live_mode_missing_key_explains_exact_configuration_error(monkeypatch):
    """Choosing Live Mode without a key yields clear configuration guidance in the UI
    rather than a misleading successful action.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    fake.mode = 'live'
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    run_page(monkeypatch, fake)
    fake.click_label = 'Check leave eligibility'
    run_page(monkeypatch, fake)
    assert 'NEBIUS_API_KEY is missing' in fake.session_state.model_problem
    assert 'completed' not in fake.session_state
    assert any(kind == 'error' and 'NEBIUS_API_KEY is missing' in str(args[0])
               for kind, args, _ in fake.messages)


def test_cli_live_missing_key_is_actionable(monkeypatch, capsys):
    """The command-line live path fails with useful missing-key guidance before
    attempting a paid or unauthorized request.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    import cli
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["cli.py", "--mode", "live", "--yes"])
    exit_code = cli.main()
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "NEBIUS_API_KEY is missing" in output
    assert "No API request was sent" in output


def test_policy_caption_does_not_misstate_current_balance(monkeypatch):
    """The browser distinguishes the fictional annual allowance from the current
    balance available for new leave.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    run_page(monkeypatch, fake)
    captions = [str(args[0]) for kind, args, _ in fake.messages if kind == 'caption']
    assert any('40h starting demo balance' in c for c in captions)
    assert not any('40h currently available' in c for c in captions)


def test_live_model_label_reflects_configured_override(monkeypatch):
    """The UI displays a configured NEBIUS_MODEL override in live mode rather than
    always labeling the default.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    fake.mode = 'live'
    monkeypatch.setenv('NEBIUS_MODEL', 'my-custom-model')
    run_page(monkeypatch, fake)
    captions = [str(args[0]) for kind, args, _ in fake.messages if kind == 'caption']
    assert any('Model: `my-custom-model`' in c for c in captions)


def test_agent_browser_mock_proposal_then_explicit_confirmation(monkeypatch):
    """The agent page exposes a mock proposal, requires a distinct confirmation event,
    then verifies a pending record.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    fake.path = "agent"
    run_page(monkeypatch, fake)
    assert fake.session_state.agent_hr_backend.balance_for("E-1001") == 12
    assert not fake.session_state.agent_hr_backend._records
    fake.click_label = "Let the agent explore alternatives"
    run_page(monkeypatch, fake)
    answer = fake.session_state.agent_result
    assert answer.proposed and answer.proposed_plan.requested_hours == 12
    assert not fake.session_state.agent_hr_backend._records
    fake.click_label = "Confirm agent proposal and submit pending request"
    run_page(monkeypatch, fake)
    assert fake.rerun_requested
    run_page(monkeypatch, fake)
    assert fake.session_state.agent_completion["verified"]
    assert fake.session_state.agent_hr_backend.balance_for("E-1001") == 0


def test_agent_browser_live_missing_key_fails_closed(monkeypatch):
    """The agent browser path fails safely without configured Live Mode credentials and
    does not create a record.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    fake.path = "agent"
    fake.mode = "live"
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    run_page(monkeypatch, fake)
    fake.click_label = "Let the agent explore alternatives"
    run_page(monkeypatch, fake)
    assert "NEBIUS_API_KEY is missing" in fake.session_state.agent_problem
    assert not fake.session_state.agent_hr_backend._records
    assert "agent_result" not in fake.session_state


def test_independent_demo_balances_in_browser(monkeypatch):
    """Fixed and agentic scenarios display independent fictional balances, avoiding
    misleading shared state.

    Scope: Offline regression test of the specified Python contract;
    not a real-model quality, cost, or latency benchmark.
    """
    fake = StreamlitStub()
    run_page(monkeypatch, fake)
    fake.path = "agent"
    run_page(monkeypatch, fake)
    assert fake.session_state.hr_backend.balance_for("E-1001") == 40
    assert fake.session_state.agent_hr_backend.balance_for("E-1001") == 12
