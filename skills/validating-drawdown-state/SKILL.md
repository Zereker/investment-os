---
name: validating-drawdown-state
description: Use when a live review depends on drawdown-cycle reconstruction, historical closing highs, executed deployment stages, or broker alert-pointer consistency.
---

# Validating Drawdown State

## Purpose

Reconstruct the current drawdown cycle from the current repository procedure and authoritative market and broker evidence. Do not copy thresholds or stage values into this skill.

## Required inputs

- the distributed policy files, including the current drawdown/state-reconstruction files;
- historical closing-price series with sufficient coverage and a declared price basis;
- current market price required by the workflow;
- corroborating evidence for stages already executed in the current cycle;
- current broker alert inventory when alert-pointer validation is required.

## Procedure

1. Determine the current historical-high closing value using the repository-defined source, price field, and coverage rule.
2. Detect whether a new high resets the cycle.
3. Reconstruct executed stages from the repository-required evidence; never infer execution from an alert alone.
4. Determine the next available stage using the current policy.
5. Run the repository's deterministic drawdown and alert-pointer tools when available.
6. Compare expected alert count, instrument, field, operator, stage identity, and price with the broker state.

## Fail closed

Return the repository-defined incomplete or review state and stop new drawdown deployment candidates when:

- history coverage or price basis is uncertain;
- executed-stage evidence conflicts;
- cycle reset state is ambiguous;
- required alert inventory is unavailable;
- the alert points to the wrong stage or price;
- policy and executable output disagree.

A correct price with a stale stage identity is still a failure. State the exact recovery condition.
