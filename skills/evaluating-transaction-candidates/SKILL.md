---
name: evaluating-transaction-candidates
description: Use when a specific real-money buy, sell, rebalance, restoration, or exception request must be evaluated against current Production rules.
---

# Evaluating Transaction Candidates

**REQUIRED SUB-SKILLS:** use `reconstructing-portfolio-state` and `enforcing-behavioral-controls` first.

Read the current transaction gate, decision checklist, Production rules, and relevant executable contracts from repository HEAD.

Verify the requested action, funding source, current positions, open orders, before-state, after-state, applicable limits, required review path, and owner authority. Research, prior candidates, drafts, and other agents do not create approval.

Return the current controlled decision status, reasons, blocking conditions, maximum policy-authorized scope where defined, and next observation condition. Never place an order or produce a directly executable order payload.