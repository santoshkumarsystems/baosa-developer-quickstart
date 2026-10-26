# Employee Leave Assistant — see the BAOSA principle in action

**Author:** Santosh Kumar · [← README](../README.md) · [Run the demo](RUN-LOCALLY.md)

## The business goal

**Correctly resolve an employee's leave request, following company rules and respecting the employee's decision.** Define what counts as correct **before** choosing whether a fixed workflow or agent helps.

The shortest verification example is:

| **SUCCESS** | **FAILURE** |
|---|---|
| Leave request submitted. **Saved record verified.** | Agent says “Submitted!” **No saved record found.** |

**BAOSA checks what happened—not what the agent claimed.** A request saved as `PENDING_APPROVAL` is **not** yet manager-approved.

## Try two implementations, same trusted rules

| Mode in the app | What it demonstrates | Who can submit? |
|---|---|---|
| **Fixed workflow** | Employee specifies exact leave dates and hours; trusted Python checks them. The demo additionally illustrates a constrained model/tool API exchange. | Only trusted Python, **after employee confirmation** |
| **Agent-assisted workflow** | Model can choose permitted tools, call order, and candidate alternatives. The example prioritizes a full Friday despite a limited balance. | The *same* confirmation-gated trusted Python code |

In the agent scenario the employee initially wants **8h Thursday + 8h Friday** but has **12h** left; full Friday is essential. **4h Thursday + 8h Friday** is an illustrative eligible proposal, *not* a required live-model answer. The agent does **not** get submit or approve tools.

## Three correct resolutions—not three different agents

1. **Policy refusal:** The request is ineligible; no record is created.
2. **Employee decline:** The proposal is eligible but not confirmed; no record is submitted.
3. **Confirmed submission:** The record is saved with exact reviewed details and independently read back as `PENDING_APPROVAL`.

The predefined outcome contract decides what counts as a correct **resolution**. Keep employee-request **fulfillment** as a separate measure. A correct refusal is not an approval.

## Mock and Live — End-to-End Flow

![BAOSA end-to-end flow: Streamlit application chooses inference mode, the client factory creates either a mock simulated Nebius client using httpx.MockTransport with no external API call, or a live OpenAI client using Nebius credentials and the Token Factory HTTPS endpoint for real model inference](images/baosa_end_to_end_flow_diagram.png)

Mock Mode has **no live Beam inference**, GPU usage, model-generated tokens or provider cost. **Live Mode** uses the developer's own configured Nebius Token Factory endpoint and is explicitly selected. Merely placing an API key in `.env` does not send any paid request.

**Go deeper:** [Agent freedom and three walls](AGENT-FREEDOM-AND-BOUNDARIES.md) · [Full code walkthrough](CODE-WALKTHROUGH.md) · [Live Mode checklist](LIVE-MODE-CHECKLIST.md) · [Business formulas](METHODOLOGY-AND-OUTCOMES.md).
