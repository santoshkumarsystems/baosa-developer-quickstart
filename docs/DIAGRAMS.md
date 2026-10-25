# BAOSA diagrams — approved visuals and editable engineering reference

**Author:** Santosh Kumar · [← README](../README.md)

**These three reference images are the approved visual design used by the GitHub README.** They are intentionally identical to the original images; do not replace them with Mermaid renderings.

## Approved diagram 1 — BAOSA methodology

![Approved BAOSA philosophy diagram](images/baosa-philosophy.png)

## Approved diagram 2 — Agent freedom

![Approved agent freedom diagram](images/agent-freedom.png)

## Approved diagram 3 — Business metrics before engineering metrics

![Approved measurement diagram](images/business-engineering-metrics.png)

---

## Supplemental editable Mermaid sketches

The following Mermaid flows are technical sketches for editing and exploration. **They are not pixel-identical to the three approved images above.** The approved images and the root README are the visual references.

## 1. Before Agents — outcomes shape the choice

```mermaid
flowchart TD
    A["BUSINESS REQUIREMENTS<br/>Who? · What? · Why?"]
    B["BUSINESS OUTCOME<br/>What must we achieve?"]
    C["SUCCESS CRITERIA<br/>How will we know?"]
    D{"DO WE NEED AN AGENT?"}
    E["FIXED WORKFLOW"]
    F["AGENT DECIDES FREELY HOW<br/>Single or Multi-Agent<br/>Tools · Order · Alternatives"]
    G["THREE TRUSTED WALLS<br/>Policy · Permissions · Confirmation"]
    H["INDEPENDENTLY VERIFY<br/>THE ACTUAL OUTCOME"]
    A --> B --> C --> D
    D -->|NO| E
    D -->|YES| F
    E --> G
    F --> G
    G --> H
    classDef neutral fill:#ffffff,stroke:#cccccc,color:#222222,stroke-width:1px
    class A,B,C,D,E,F,G,H neutral
```

The **No** path has no agent autonomy; the **Yes** path gives agent(s) freedom to choose their permitted execution approach. **Both** paths have relevant business controls, which trusted code applies **throughout execution**. [What is BAOSA? →](METHODOLOGY-AND-OUTCOMES.md).

## 2. Agent autonomy — freedom of approach, not authority

```mermaid
flowchart TD
    A["BUSINESS GOAL<br/>Outcome and success criteria already defined"]
    B["AGENT DECIDES FREELY HOW<br/>Permitted tools · Order · Alternatives"]
    C["THREE NON-NEGOTIABLE WALLS<br/>Policy · Permissions · Confirmation"]
    D["INDEPENDENT VERIFICATION<br/>Read real application state"]
    A --> B --> C --> D
    classDef neutral fill:#ffffff,stroke:#cccccc,color:#222222,stroke-width:1px
    class A,B,C,D neutral
```

The walls are **trusted application checks**, not a fixed sequence that the model must follow. The model may propose; it cannot make an unauthorized submission. [How it's enforced →](AGENT-FREEDOM-AND-BOUNDARIES.md).

## 3. Measure WHAT. Optimize HOW.

```mermaid
flowchart TD
    A["1. BUSINESS METRICS — WHAT?<br/>Verified Success Rate · Cost per Verified Success"]
    B["2. ENGINEERING METRICS — HOW?<br/>Latency · Tokens · Tool Calls · GPU Utilization"]
    C["OPTIMIZE COST & PERFORMANCE<br/>Preserve verified success and business constraints"]
    A --> B --> C
    classDef neutral fill:#ffffff,stroke:#cccccc,color:#222222,stroke-width:1px
    class A,B,C neutral
```

[Business formulas and measurement limitations →](BUSINESS-AND-ENGINEERING-METRICS.md).
