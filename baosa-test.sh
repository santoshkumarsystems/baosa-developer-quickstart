#!/usr/bin/env bash
set -euo pipefail

# Works from a clone, and through a ~/baosa-test.sh symlink.
SCRIPT="$(realpath "${BASH_SOURCE[0]}")"
cd "$(dirname "$SCRIPT")"

if [[ ! -x .venv/bin/python ]]; then
    echo 'Missing .venv. Follow docs/RUN-LOCALLY.md to install dependencies.' >&2
    exit 1
fi

.venv/bin/python -m pytest -v --tb=short --no-header tests

GREEN='' RESET=''
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    GREEN=$'\033[32m'
    RESET=$'\033[0m'
fi

check() { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }

printf '\n============================================================\n'
printf '           BAOSA — ENGINEERING VALIDATION SUMMARY\n'
printf '============================================================\n\n'
printf '1. AGENT FREEDOM\n   test_agent_freely_selects_different_permitted_tool_order\n'
check 'The agent can select permitted tools in different orders.'
printf '\n2. THREE WALLS — EXPLICIT CONFIRMATION\n   test_agent_proposal_requires_explicit_boolean_confirmation\n'
check 'No submission without actual Boolean confirmation.'
printf '\n3. POLICY ENFORCEMENT\n   test_agent_cannot_reduce_high_priority_friday_to_fit\n'
check 'The full-Friday requirement cannot be overridden.'
printf '\n4. NEBIUS-COMPATIBLE SIMULATED API\n   test_simulated_endpoint_emits_tool_call_in_openai_compatible_envelope\n'
check 'Tool calls use the OpenAI-compatible response structure.'
printf '\n5. VERIFIED BUSINESS OUTCOME\n   test_happy_path_creates_pending_record_and_reads_back\n'
check 'Pending leave is saved and independently read back.'
printf '\n============================================================\n'
printf '              %sALL TESTS PASSED%s\n' "$GREEN" "$RESET"
printf '   Freedom of approach. Not freedom of authority.\n'
printf '============================================================\n'
