# Investment OS — Product Boundary

Investment OS is one long-term investment Agent. Its purpose is to turn fresh portfolio facts and published policy into a clear decision and a verifiable next trigger—not to predict markets or manufacture trades.

## Authority map

Each concern has one source of truth:

- `SKILL.md` — Agent behavior and task routing;
- `00-constitution.md` — mandate, investment universe, allocation, limits, and active registry;
- `01-operating-manual.md` — daily, monthly, periodic, state-reconstruction, and review procedures;
- `02-data-contract.md` — authoritative sources, freshness, field definitions, and data gates;
- `03-journal.md` — approved durable context and lessons;
- `agent-execution-contract.md` — portable authorization and broker-write boundary.

This file defines only the product boundary. It must not duplicate investment parameters or detailed procedures.

When policy conflicts, apply `00-constitution.md`, then `01-operating-manual.md`, then `03-journal.md`. `02-data-contract.md` controls whether facts are usable; it does not create investment policy. An installed session executes its distributed snapshot and does not fetch a newer checkout at runtime.

## Decision loop

```text
Observe → Understand → Decide → Monitor → Repeat
```

- Observe authoritative facts.
- Understand their meaning under current policy.
- Decide with the shortest sufficient explanation.
- Monitor one objective condition that would change the decision.
- Execute only through the separate authorization boundary.

`HOLD` is a complete successful decision.

## Responsibility boundary

**代码验证事实并保护执行，LLM 负责投资判断。**

Deterministic tools own source validation, reconciliation, arithmetic, policy mirrors, authorization binding, broker submission, and read-back verification. The LLM owns evidence selection, interpretation, comparison, recommendation, and explanation. Neither may invent missing facts or silently change published policy.

## Product invariants

### Repository Stores Knowledge, Never Portfolio

The public repository may contain policy, formulas, synthetic tests, public evidence, and tools. It must not contain account identifiers, NAV, cash, positions, orders, fills, contributions, tax data, authorization records, or execution receipts.

### Runtime Data Is Ephemeral

Live account state and broker results exist only in the trusted runtime or current private session. Pasted numbers, screenshots, old reports, memory, and another Agent's output are context—not account authority.

### Fail closed only the affected path

Missing, stale, conflicting, or unavailable facts remain unknown. Stop every decision or operation that requires them, name the blocker and recovery condition, and continue unaffected analysis or routine paths when policy permits.

### Production remains closed

Only assets and actions authorized by `00-constitution.md` may enter Production. Research may challenge policy, but it does not become Production until the owner approves the change, authoritative files are updated, required checks pass, and a new distribution is released.

### Recommendation is not execution

A recommendation, candidate, prior approval, another Agent's conclusion, or Investment Committee result does not authorize a broker write. **IC 结论不是 Broker 授权。** Execution requires one explicit owner-authorized operation in the current session and authoritative read-back verification.

## Product outputs

Daily Review follows the canonical Skill and the operating manual. It starts from the portfolio, not headlines, and returns:

```text
Portfolio
Change
Decision
Reason
Next Trigger
```

Monthly funding, transaction judgment, research, periodic review, and system audit use their procedures in `01-operating-manual.md`. Exact investment parameters always come from the numbered policy files, never from this contract.

## Change rule

Prefer deleting or editing an existing rule over creating a new file, field, status, layer, or Skill. New structure must be justified by a real observed failure that existing rules cannot safely resolve.

Every repository change must preserve the privacy boundary, keep policy and implementation aligned, and pass the canonical static suite. Static tests do not prove real Agent behavior:

```text
Real Harness behavior: NOT YET VERIFIED
```

Installing the plugin never grants broker access, changes investment policy, or authorizes a transaction.
