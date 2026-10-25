# Nebius Live Mode — explicit opt-in checklist

**Author:** Santosh Kumar · [← Local setup](RUN-LOCALLY.md)

**Important:** BAOSA defaults to **Mock Mode**, even with valid credentials. A configured key **does not** automatically make a network request or switch modes. Live calls may incur provider charges.

## 1. Install and start offline

From the project root, in your activated Python virtual environment:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

You can explore Mock Mode without any API key. The optional development test dependencies are **not required** to run the demo.

## 2. Configure Nebius privately

```bash
cp .env.example .env
```

Edit `.env` on your machine:

```dotenv
NEBIUS_API_KEY=replace-with-your-own-key
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=reflection/beam
```

| Variable | Purpose |
|---|---|
| `NEBIUS_API_KEY` | **Required for Live Mode.** Keep secret, never commit. |
| `NEBIUS_BASE_URL` | Optional API endpoint; the shown Token Factory URL is the app default. |
| `NEBIUS_MODEL` | Optional model identifier; `reflection/beam` is the demo candidate, subject to actual account availability. |

`.env` is Git-ignored; existing shell variables take precedence. Do not paste secrets into screenshots, chats, issues or logs. Verify account credits, model availability, and billing settings before Live Mode.

## 3. Explicitly exercise real inference

**Browser:** Restart Streamlit if needed, choose **Live · Nebius Token Factory** in the sidebar, then **trigger the workflow action**. Selecting Live alone checks local settings; the action initiates the provider request.

**CLI (fixed workflow only):**

```bash
python cli.py --mode live
```

The CLI asks for explicit `YES` before saving its fictional pending record. Do **not** add `--yes` unless you intentionally want to approve that exact demo submission. The CLI is not the agentic path; use Streamlit for the agent scenario.

## 4. What to verify during the live trial

Check the actual provider response and model/tool trace, then confirm trusted Python still enforces policy, actor scope, **employee confirmation**, pending-only submission and independent record readback. A valid API response alone is **not** evidence of a verified HR outcome.

The source retains Beam tool-call IDs and reasoning history where applicable; the mock only tests the shape of this exchange. **No successful real Beam run or benchmark is claimed in this offline package.**

## 5. Troubleshooting

| Symptom | Check |
|---|---|
| Missing-key warning | `.env` location, key spelling, shell overrides; restart process |
| 401 / 403 | Key validity and model/account access |
| 402 / 429 | Credits, billing, quota or rate limits |
| 400 / 404 | Model ID, request features, endpoint URL |
| Network timeout | Internet, proxy/TLS, endpoint reachability |
| Mock still selected | **Explicitly select Live and trigger a workflow** |

Never post credentials or full provider payloads publicly. [Extended local troubleshooting](RUN-LOCALLY.md#troubleshooting) · [Why this platform and model?](DECISIONS.md).
