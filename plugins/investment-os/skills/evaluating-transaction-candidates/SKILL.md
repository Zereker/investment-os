---
name: evaluating-transaction-candidates
description: Use when a specific real-money buy, sell, rebalance, restoration, or exception request must be evaluated against current Production rules.
---

# Evaluating Transaction Candidates

Use fresh portfolio state and behavioral controls when the request concerns a live account.

Code verifies the requested action, funding source, positions, open orders, before-state, after-state, arithmetic, hard limits and execution capability. These facts must not be invented or silently changed.

The LLM owns the investment judgment. It may select relevant valuation, trend, macro, thesis and opportunity-cost evidence; weigh conflicting signals; reject an apparently valid formula result; or recommend `HOLD`, `BUY`, `SELL`, `WAIT` or further research. Do not reduce the decision to a universal score or require every candidate to pass the same fixed indicator stack.

Apply current policy as the mandate, while clearly separating:

- the recommendation under current policy; and
- any proposal to change the policy itself.

Return the recommendation, the few decisive reasons, material uncertainty, any blocking fact or policy limit, and the next condition that would change the conclusion. Avoid exhaustive checklists when they add no decision value.

A candidate decision is not execution authority. An exact broker operation may proceed only after current-session owner authorization, supported adapter capability, one submission attempt and authoritative read-back verification.
