# Risk Scoring Reference

## Overview

The deployment risk score is a deterministic **0–100 integer** computed from
six independent, additive factors.  Each factor has a fixed maximum contribution
so the model is transparent and auditable.

```
Total Score = Σ(factor scores)  capped at 100
```

## Risk Levels

| Level    | Score Range | Recommended Action |
|----------|-------------|-------------------|
| LOW      | 0 – 30      | Standard release pipeline. No additional gate. |
| MEDIUM   | 31 – 60     | Deploy with monitoring. Notify on-call team. |
| HIGH     | 61 – 80     | Senior engineer review + rollback plan required. |
| CRITICAL | 81 – 100    | Block deployment. Tech lead escalation + full regression. |

## Factor Breakdown

### Factor 1 — Change Volume (max 20 pts)

Measures the raw number of files changed in this deployment.

| Changed Files | Points |
|---------------|--------|
| 1 – 5         | 4      |
| 6 – 10        | 8      |
| 11 – 20       | 14     |
| > 20          | 20     |

**Rationale:** More changed files → larger blast radius → higher coordination risk.

---

### Factor 2 — Transitive Spread (max 20 pts)

Measures how many additional modules are affected via import chains.

| Transitively Affected | Points |
|-----------------------|--------|
| 0 – 10                | 0 – 5  |
| 11 – 20               | 8      |
| 21 – 50               | 14     |
| > 50                  | 20     |

**Rationale:** Shared utilities and base classes with many dependents amplify
the blast radius far beyond the changed files themselves.

---

### Factor 3 — API Contract Violations (max 25 pts)

Each **breaking** API contract change adds up to 10 points (capped at 25).

| Breaking Changes | Points |
|------------------|--------|
| 0                | 0      |
| 1                | 10     |
| 2                | 20     |
| ≥ 3              | 25     |

**Rationale:** Breaking changes to API contracts force coordinated consumer
upgrades and are the most common cause of production incidents during releases.

---

### Factor 4 — Module Type Risk (max 20 pts)

Awarded cumulatively based on the *types* of modules in the blast radius.

| Module Type Changed | Points |
|--------------------|--------|
| Database / migrations | +10 |
| API endpoints          | +6  |
| Config / infrastructure| +4  |

**Rationale:** Database changes are irreversible without migrations. API changes
affect consumers. Config changes affect the entire runtime environment.

---

### Factor 5 — Sensitivity (max 10 pts)

Checks for security-sensitive and financially critical code in the blast radius.

| Sensitivity         | Points |
|--------------------|--------|
| Auth / security code | +5   |
| Payment / billing code | +5 |

**Rationale:** Defects in auth or payment code have outsized business and
regulatory impact compared to equivalent defects elsewhere.

---

### Factor 6 — Consumer Breadth (max 5 pts)

Counts distinct top-level service directories in the blast radius (proxy for
downstream consumer applications).

| Consumer Apps | Points |
|---------------|--------|
| 0             | 0      |
| 1             | 1      |
| 2             | 2      |
| 3             | 3      |
| 4             | 4      |
| ≥ 5           | 5      |

**Rationale:** The more consumers affected, the higher the coordination and
communication cost of the release.

## Example Calculations

### Example A — Low-Risk Hotfix

```
Changed files:  2  → Factor 1 = 4 pts
Transitive:     3  → Factor 2 = 1 pt
Breaking APIs:  0  → Factor 3 = 0 pts
Module types:   service → Factor 4 = 0 pts
Sensitivity:    none → Factor 5 = 0 pts
Consumers:      1  → Factor 6 = 1 pt
─────────────────────────────
Total           = 6 pts → LOW
```

### Example B — High-Risk API Refactor

```
Changed files:  15 → Factor 1 = 14 pts
Transitive:     35 → Factor 2 = 14 pts
Breaking APIs:  2  → Factor 3 = 20 pts
Module types:   api_endpoint + config → Factor 4 = 10 pts
Sensitivity:    auth code → Factor 5 = 5 pts
Consumers:      3  → Factor 6 = 3 pts
─────────────────────────────
Total           = 66 pts → HIGH
```

### Example C — Critical Database Migration

```
Changed files:  8  → Factor 1 = 8 pts
Transitive:     60 → Factor 2 = 20 pts
Breaking APIs:  1  → Factor 3 = 10 pts
Module types:   database + api + config → Factor 4 = 20 pts
Sensitivity:    payment code → Factor 5 = 5 pts
Consumers:      5  → Factor 6 = 5 pts
─────────────────────────────
Total           = 68 pts (but DB migration alone → CRITICAL threshold)
```

## Extending the Scoring Model

The `RiskScorer` class is intentionally simple.  Teams can extend it by:

1. Adding a **test coverage factor** — penalise areas with < 60% coverage.
2. Adding a **deployment frequency factor** — first deploy in 30+ days is riskier.
3. Adding a **time-of-day factor** — deploys outside business hours carry
   higher incident response cost.
4. Integrating a **historical incident database** — files that caused incidents
   before get a permanent risk premium.
