# Run BAOSA locally — bring your own credentials

**Your machine. Your key. Your budget.** No public web form ever asks for a key. You can inspect every source file before enabling real inference.

## Prerequisites
- Git; **Python 3.10 or newer**; internet access for package installation.
- **Only for Live Mode:** a Nebius Token Factory account, model access, API key and active credits/billing as required by Nebius.

## 1. Clone and install

Replace `<YOUR-GITHUB-USERNAME>` with the actual publisher account **once this repository is uploaded**:

```bash
git clone https://github.com/<YOUR-GITHUB-USERNAME>/baosa-developer-quickstart.git
cd baosa-developer-quickstart
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On **Windows PowerShell** use `py -m venv .venv` and `.venv\Scripts\Activate.ps1` instead of the Unix activation command. If your shell restricts script execution, use `.venv\Scripts\python.exe` to run commands without activation.

For the supplied ZIP instead of a GitHub clone: extract it, enter the `baosa-developer-quickstart` folder and start at `python3 -m venv .venv`.

## 2. Start safely in Mock Mode

```bash
python -m streamlit run app.py
```

Open **http://localhost:8501**, select **Mock · offline and free**, and try each workflow. The mocked request and response use an **in-memory HTTP transport**: the JSON envelope models `/v1/chat/completions` and tool calls, but **no actual network endpoint, Nebius account, Beam model, or real inference runs**. The agent's choices are scripted.

## 3. Optional real Beam inference

Create a local file from the sample:

```bash
cp .env.example .env
```

Windows PowerShell: `Copy-Item .env.example .env`.

Edit **`.env` on your computer**:

```dotenv
NEBIUS_API_KEY=replace-with-your-own-api-key
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=reflection/beam
```

The application loads this file locally with `python-dotenv`. `.env` is excluded from Git by `.gitignore`. **Do not commit it, share screenshots of it, or paste credentials into issues.** Environment variables already set in your shell take precedence over `.env` values.

**How to exercise the configured credentials:** configuring `.env` alone does not make a paid call. The application intentionally starts in **Mock Mode**; this prevents surprise charges. To actually exercise the configured Nebius endpoint, **select Live Mode explicitly** in the Streamlit sidebar, then click the workflow action. Alternatively, from the repository root run:

```bash
.venv/bin/python cli.py --mode live
```

To test without spending credits, use:

```bash
.venv/bin/python cli.py --mode mock --yes
./baosa-test.sh
```

**When your key arrives:** (1) replace the placeholder in `.env`; (2) verify your account has access to `reflection/beam` and credits; (3) restart Streamlit; (4) select **Live**; (5) invoke the workflow; (6) inspect its tool trace, trusted policy decision, confirmation and verified saved record. A 401/403/402/404 or model incompatibility means the provider-side setup still needs attention. Never paste the key into chat, logs, or screenshots.

Restart the Streamlit process, select **Live · Nebius Token Factory**, and invoke a workflow. Live Mode connects to the provider you configured; usage may be billed to your account. No real Beam result has been evaluated or certified by this repository.

**Before spending credits:** inspect `baosa/inference.py`, `baosa/agent.py`, and the tool permissions; verify Nebius account access, pricing and any spending protections. Model calls have bounded step counts and output token requests, **not a hard monetary spending guarantee**. Retries are disabled in the OpenAI client. In Live Mode a fixed workflow may make model calls despite not needing an autonomous agent.

## 4. Optional for developers: run the tests and five-test summary

**The demo already runs after Steps 1–2; you do not need pytest to explore it.** If you want to inspect the test suite, install the development dependencies **once** (includes `pytest` and all application dependencies):

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
```

**Windows Subsystem for Linux (WSL), Linux or macOS:**

```bash
./baosa-test.sh
```

The command lists every test with `PASSED`/`FAILED`. **Only after the full suite passes**, it shows five key engineering examples—agent freedom, confirmation, policy, simulated API structure and verified outcome—with **green checkmarks in an interactive terminal**.

If you prefer the exact short command `~/baosa-test.sh` used in our WSL walkthrough, create a shortcut **once while inside the cloned repository**:

```bash
ln -sf "$PWD/baosa-test.sh" "$HOME/baosa-test.sh"
~/baosa-test.sh
```

This shortcut points to the script in this clone; after updating the repository, it uses the latest committed test script. Do not copy a stale script into your home directory.

**Windows PowerShell** (run from repository root, after installing `requirements-dev.txt`):

```powershell
.\.venv\Scripts\python.exe -m pytest -v --tb=short --no-header tests
```

The WSL/Linux/macOS test script provides the additional five-test presentation summary. Windows users can run the same tests with the command above.

### Optional fresh-clone quality check (recommended after publishing on GitHub)

Start in an **empty directory**, replace `<YOUR-GITHUB-USERNAME>` with the published owner, and run:

```bash
git clone https://github.com/<YOUR-GITHUB-USERNAME>/baosa-developer-quickstart.git
cd baosa-developer-quickstart
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip check
./baosa-test.sh
.venv/bin/python cli.py --mode mock --yes
```

This verifies package installation, dependency consistency, the full offline test suite and the mock fixed-workflow CLI **from a clean clone**. It doesn't require a Nebius key. If you already installed dependencies following step 1, there is no need to reinstall them every time you run tests. GitHub also runs [fresh-install CI checks](../.github/workflows/validate.yml) on each push and pull request; review the Actions results after publishing.

The CLI exercises the fixed workflow only. Passing offline tests validates the covered application behavior, not live model accuracy or provider performance. [What the highlighted tests actually check →](TESTING.md).

## Troubleshooting

| Symptom | Check |
|---|---|
| Missing API key | `.env` file exists at project root; restart app; use `NEBIUS_API_KEY` |
| HTTP 401/403 | Key validity and account/model access |
| HTTP 402/429 | Billing, available credits, or provider quota |
| HTTP 400/404 | Model ID, request compatibility, and base URL |
| Connection failure | Network/TLS/proxy/endpoint; no secret in logs |
| UI on a different port | Read the URL printed by Streamlit |

**Official resources:** [Token Factory](https://nebius.com/services/token-factory) · [Beam integration cookbook](https://dev.nebius.com/cookbook/beam-reflection-token-factory).

## Review code documentation

Every class, function, and test includes a docstring describing its responsibility or tested behavior. See [Source Code Guide](SOURCE-CODE-GUIDE.md) for the reading order and architecture boundaries.

```bash
python scripts/check_docstrings.py
./baosa-test.sh
```

**Author: Santosh Kumar** · [Back to 30-second README](../README.md) · [Business outcome methodology](METHODOLOGY-AND-OUTCOMES.md)
