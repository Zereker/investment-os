---
name: broker-runtime
description: Use when an Investment OS task needs live broker account data, capability discovery, runtime-state validation, or a fail-closed decision about missing broker inputs.
---

# Broker Runtime

## Goal

Expose one broker-neutral runtime contract for Investment OS. Domain skills consume this contract; they do not depend on a specific broker, connector, API, screenshot, or pasted account summary.

## Required runtime capabilities

Discover and read the capabilities required by the policy files distributed with this skill. The runtime contract may include:

- account identity and account type;
- account summary and net liquidation value;
- balances and cash by relevant currency;
- positions with quantities, prices, market values, and timestamps;
- open and pending orders, including duplicates and conflicting instructions;
- cash transactions or contribution evidence when a funding workflow needs them;
- quotes or market series when required by current policy;
- broker alert inventory required for drawdown-pointer validation;
- standing broker automations, including dividend reinvestment and recurring-investment settings, when the adapter exposes them;
- source, snapshot time, timezone, currency basis, and freshness for every component.

A capability is `available`, `unavailable`, `stale`, or `conflicting`. Never replace an unavailable capability with an estimate, prior value, manual figure, screenshot, or another agent's output.

## Normalized output

Produce an ephemeral Broker Runtime with these top-level sections:

1. `identity`
2. `snapshot`
3. `capabilities`
4. `account_summary`
5. `balances`
6. `positions`
7. `open_orders`
8. `cash_transactions`
9. `market_inputs`
10. `alert_inventory`
11. `standing_automations`
12. `observations`
13. `reconciliation`
14. `blocking_issues`
15. `runtime_status`

`observations` records `source`, `observed_at`, and any provider `source_as_of` separately for each capability. A single orchestration timestamp does not prove that every endpoint is fresh.

An unavailable capability must carry `null`, never `0`, `{}`, or `[]`. Empty collections are authoritative facts only after a successful read. This distinction is mandatory for orders, alerts, cash transactions, and standing automations.

`runtime_status` is `PASS` only when every capability required for the current task is present, fresh, internally consistent, and attributable to an authoritative runtime source. Otherwise it is `DATA INCOMPLETE`.

## Reconciliation

At minimum, reconcile the account and task-specific facts required by the policy files distributed with this skill:

- position market values and cash against account-level values;
- currencies and conversion basis;
- duplicate, overlapping, stale, or contradictory open orders;
- unknown or out-of-universe positions;
- snapshot timestamps and source freshness;
- contribution evidence for funding workflows;
- any task-specific broker alert, order, or state pointer required by current policy.

Do not invent tolerances. Read current repository rules and deterministic tools for the applicable reconciliation criteria.

## Adapter boundary

A broker adapter translates a concrete source into this runtime contract. IBKR may be the current adapter, but the Skill must remain broker-neutral. A CSV, paper-account, mock, or another broker adapter is acceptable only when the task and repository policy explicitly authorize it.

Adapters must not:

- persist real account data in the public repository;
- omit unsupported fields without declaring them unavailable;
- convert missing data into zero, empty collections, or stale cached values;
- perform transactions or produce directly executable order instructions.

## Fail-closed matrix

- Missing positions or balances: portfolio state is `DATA INCOMPLETE`.
- Missing open orders: no new transaction candidate may be authorized.
- Missing cash transactions or contribution evidence: Routine DCA and contribution-based funding are `DATA INCOMPLETE`.
- Missing required market inputs: the affected valuation, drawdown, or deployment path is `DATA INCOMPLETE`.
- Missing alert inventory: alert-pointer validation and drawdown deployment are `DATA INCOMPLETE`; do not substitute an empty alert list.
- Missing cash transactions: contribution-funded channels are `DATA INCOMPLETE`; do not substitute zero contribution.
- An active standing automation that can add an out-of-universe asset is a control blocker until reviewed; do not mutate the broker setting automatically.
- Stale or conflicting snapshots: stop the affected workflow until refreshed and reconciled.

Return the exact missing capability, affected workflow, runtime status, and next verifiable action. Keep all real account data ephemeral.
