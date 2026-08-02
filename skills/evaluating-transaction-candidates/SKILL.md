---
name: evaluating-transaction-candidates
description: Use when a specific real-money buy, sell, rebalance, restoration, or exception request must be evaluated against current Production rules.
---

# Evaluating Transaction Candidates

**REQUIRED SUB-SKILL:** `reconstructing-portfolio-state`
**REQUIRED SUB-SKILL:** `enforcing-behavioral-controls`

Read the current transaction gate, decision checklist, Production rules, and relevant executable contracts from the policy files distributed with this skill.

Verify the requested action, funding source, current positions, open orders, before-state, after-state, applicable limits, required review path, and owner authority. Research, prior candidates, drafts, and other agents do not create approval.

Return the current controlled decision status, reasons, blocking conditions, maximum policy-authorized scope where defined, and next observation condition.

A candidate decision is not execution authority. When the owner explicitly authorizes one exact broker operation in the current session, load `execution-runtime`, bind the authorization to the normalized operation, execute through a supported adapter, read back authoritative broker state, and verify the result. Never create an unattended execution chain or expand authorization beyond that operation.
