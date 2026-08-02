---
name: running-daily-review
description: Use when the user asks what happened in the live portfolio today, what needs attention, or what actions are currently authorized under Production rules.
---

# Running Daily Review

**REQUIRED SUB-SKILLS:** use `reconstructing-portfolio-state` and `enforcing-behavioral-controls` first.

Read the current daily workflow and report contract from repository HEAD. Use only fresh authoritative runtime inputs and current executable mirrors.

Produce the repository-defined daily sections, clearly separating facts, rule interpretation, candidates, blockers, and next observation conditions. A candidate is eligible for human review only; it is not approval or an order.

If any required state, market input, execution state, or control gate is incomplete, return the current fail-closed status and stop new transaction candidates. Never substitute an old report or manual figures.