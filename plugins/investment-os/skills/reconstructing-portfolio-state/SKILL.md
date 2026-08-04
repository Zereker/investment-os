---
name: reconstructing-portfolio-state
description: Use when a live portfolio, cash, position, order, drawdown, or transaction decision depends on current broker and market state.
---

# Reconstructing Portfolio State

**REQUIRED SUB-SKILL:** `broker-runtime`

## Goal

Build current portfolio state from a validated broker-neutral runtime before any Production conclusion.

## Procedure

1. Require a Broker Runtime whose capabilities and freshness have been evaluated for the current task.
2. Verify account identity, endpoint-level observation timestamps, timezone, currency basis, positions, balances, active orders, alert inventory, and exposed standing automations through that runtime. A global orchestration timestamp does not establish endpoint freshness.
3. Obtain the market inputs required by current policy and executable mirrors. Preserve live last and last completed daily close as distinct observations; never let an incomplete current bar become the close used for drawdown state.
4. Reconstruct non-price state using the current repository procedure; never infer it from an old report.
5. Run current deterministic repository tools for reconciliation and state checks.
6. Preserve the Broker Runtime's blocking issues; portfolio reconstruction cannot downgrade or hide them.

Manual figures, screenshots, pasted tables, cached summaries, and prior agent outputs are context only. They are never authoritative account state and cannot upgrade a Broker Runtime from `DATA INCOMPLETE` to `PASS`.

An unavailable capability is `null`. Empty collections are facts only after an authoritative successful read. In particular, do not convert unavailable cash activity to zero contribution or unavailable alert inventory to no alerts.

## Failure behavior

If the Broker Runtime is missing, stale, contradictory, cannot reconcile, or lacks a capability required by the task, return `DATA INCOMPLETE`. Do not produce a new transaction candidate.

Keep all real account data ephemeral. Never write it to the public repository, fixtures, Issues, pull requests, logs, screenshots, or durable reports.
