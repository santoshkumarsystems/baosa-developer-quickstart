# BAOSA source code: responsibilities and reading order

**Goal:** enable a new developer to understand *why* each module exists, where authority resides, and which tests establish each behavior. Each class, function and test includes a source-level docstring explaining responsibilities, boundaries or expected assertions; the longer core-method docstrings include input/output contracts and safety invariants.

## Read the code in this order

| Module | Responsibility | Key invariant |
|---|---|---|
| `baosa/policy.py` | Plans, daily hours, validation and date constraints | Policy is enforced in Python, never delegated to a model |
| `baosa/hr.py` | Fictional HR state, access checks, quotes, pending leave and read-back | Only the trusted backend can create a leave record |
| `baosa/workflow.py` | Prepare/complete lifecycle | No write before explicit confirmation; verify saved record |
| `baosa/inference.py` | Fixed-workflow model/tool exchange and endpoint configuration | Model outputs are untrusted proposals |
| `baosa/agent.py` | Agent's free selection of permitted tools and alternatives | Tool order is flexible; authority is not |
| `baosa/mock_endpoint.py` | OpenAI-compatible simulated request/response contract | Representative fixtures, not Beam reasoning or GPU performance |
| `app.py` | Streamlit UI and state transitions | Changing inputs invalidates prior proposals |
| `cli.py` | Terminal entry point | Uses the same trusted application components |

## Tests: what they defend

| File | Main regression risk |
|---|---|
| `tests/test_policy.py` | Incorrect dates, hours, balances or policy decisions |
| `tests/test_workflow.py` | Unconfirmed/unauthorized writes or false success claims |
| `tests/test_agent.py` | Loss of agent freedom or bypassing the three walls |
| `tests/test_inference.py` | Unsafe tool arguments, malformed model/provider behavior |
| `tests/test_mock_endpoint_contract.py` | Divergence from the expected chat-completions request/response shape |
| `tests/test_app_smoke.py` | UI state, missing-key diagnostics and user-flow regressions |

Run `./baosa-test.sh` to display individual test results and the five highlighted engineering checks. The full test names and purpose statements are documented beside the tests themselves.

## Boundaries

The simulated API reproduces the selected request/response envelope and deterministic tool interactions; it does not reproduce the model's reasoning. A passing offline suite validates the tested application contracts, not a provider's real latency or model quality.

## Method and test documentation standard

Every public class/function and test has a docstring. Test docstrings identify the
scenario and representative assertions; read the test body for the exact inputs and
expected outputs. Source comments distinguish model-proposed actions from trusted
Python policy, authorization, explicit confirmation, and independent readback.

**Live configuration:** see [Live Mode Checklist](LIVE-MODE-CHECKLIST.md) and
[Run Locally](RUN-LOCALLY.md). A configured API key does not auto-select live mode.
Select live explicitly to avoid unintended paid calls.

## What "documented" means in this project

- **Modules:** Begin with purpose, authority boundary, limitations and author.
- **Methods/classes:** Explain *what* the method accomplishes and *why* it belongs at this trust boundary; include arguments, return values and invariants for nontrivial API functions. The body remains readable Python rather than line-by-line prose commentary.
- **Tests:** Every test describes the scenario, the contract being protected, and the expected evidence. Synthetic test clients are labeled as fixtures, never as real inference.
- **Authorization:** Only Python policies, actor checks and literal confirmation may permit a write. The model's natural-language response never supplies proof of submission.
- **Learning path:** Start with `baosa/policy.py` → `baosa/hr.py` → `baosa/workflow.py` → `baosa/agent.py` → `baosa/inference.py` and `baosa/mock_endpoint.py` → `app.py` → the matching `tests/` module.

**Optional validation:** `python scripts/check_docstrings.py` checks structural coverage of source and test docstrings, but reviewers should still judge their correctness and clarity. [Business-first methodology](METHODOLOGY-AND-OUTCOMES.md).

**Author: Santosh Kumar**
