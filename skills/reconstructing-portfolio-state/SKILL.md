---
name: reconstructing-portfolio-state
description: Use when a live portfolio, cash, position, order, drawdown, or transaction decision depends on current broker and market state.
---

# Reconstructing Portfolio State

## Goal

Build current state from authoritative runtime sources before any Production conclusion.

## Procedure

1. Read every broker source required by current repository HEAD.
2. Verify account identity, timestamps, timezone, currency basis, positions, balances, and active orders.
3. Obtain the market inputs required by current policy and executable mirrors.
4. Reconstruct non-price state using the current repository procedure; never infer it from an old report.
5. Run current deterministic repository tools for reconciliation and state checks.

Manual figures, screenshots, pasted tables, cached summaries, and prior agent outputs are context only. They are never authoritative account state.

## Failure behavior

If a required source is missing, stale, contradictory, or cannot reconcile, return `DATA INCOMPLETE`. Do not produce a new transaction candidate.

Keep all real account data ephemeral. Never write it to the public repository, fixtures, Issues, pull requests, logs, screenshots, or durable reports.