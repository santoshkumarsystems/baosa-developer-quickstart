# BAOSA tests — optional engineering evidence

**Author:** Santosh Kumar · [← README](../README.md)

**Visitors can run the demo without pytest.** The regression suite is useful for developers who want to inspect the trusted walls, simulated API integration, and saved-record verification.

## Run the offline suite

From the repository root, after [installing Python and dependencies](RUN-LOCALLY.md):

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
./baosa-test.sh
```

The script lists each test case and its PASS/FAIL result. **Only if all tests pass** will it display five highlighted engineering checks with green terminal checkmarks. No Nebius key or network inference is required. The current package contains **100 parameterized test cases** across six modules; future changes may change this count.

### Your short WSL shortcut

Create it once **from inside the project root**, rather than copying an obsolete script:

```bash
ln -sf "$PWD/baosa-test.sh" "$HOME/baosa-test.sh"
~/baosa-test.sh
```

## Five important checks

| Principle | Test | What it verifies |
|---|---|---|
| **Agent freedom** | `test_agent_freely_selects_different_permitted_tool_order` | Multiple permitted tool sequences work; there is no mandatory hardcoded tool order. |
| **Confirmation wall** | `test_agent_proposal_requires_explicit_boolean_confirmation` | Proposal alone is not consent; submission requires actual Boolean confirmation. |
| **Policy wall** | `test_agent_cannot_reduce_high_priority_friday_to_fit` | The agent cannot sacrifice the non-negotiable full Friday just to fit the leave balance. |
| **Simulated API contract** | `test_simulated_endpoint_emits_tool_call_in_openai_compatible_envelope` | Local scripted tool replies have the expected OpenAI-compatible structure. |
| **Verified outcome** | `test_happy_path_creates_pending_record_and_reads_back` | Trusted code reads back a real **fictional in-memory** pending record instead of believing model text. |

Other tests cover actor permissions, forbidden tools, malformed arguments, provider errors, stale/reused quotes, UI behavior, and fail-closed verification. [Source guide](SOURCE-CODE-GUIDE.md) · [Trust boundaries](AGENT-FREEDOM-AND-BOUNDARIES.md).

## Fresh-clone validation after publishing

Follow the [exact clean-clone commands](RUN-LOCALLY.md#optional-fresh-clone-quality-check-recommended-after-publishing-on-github). They install from scratch, run `pip check`, execute the offline suite, and exercise the mock CLI. This checks dependency installation separately from a pre-existing virtual environment.

The repository also includes [GitHub Actions fresh-install checks](../.github/workflows/validate.yml). **The workflow's presence is not proof that a GitHub run passed.** Review actual job results once published.

## What passing does *not* establish

Passing tests does **not** certify a defect-free product, real Beam reasoning quality, Nebius provider availability, measured latency, GPU performance, actual cost per successful business outcome, or production HR security. Tests are synthetic and exercise specified **code contracts**. [Evaluation boundaries](SECURITY-AND-EVALUATION.md) · [Measurement guide](BUSINESS-AND-ENGINEERING-METRICS.md).
