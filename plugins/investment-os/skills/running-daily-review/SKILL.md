---
name: running-daily-review
description: Use when the user asks what happened in the live portfolio today, what needs attention, or what actions are currently authorized under Production rules.
---

# Running Daily Review

**REQUIRED SUB-SKILLS:** use `reconstructing-portfolio-state` and `enforcing-behavioral-controls` first.

Read the current daily workflow and report contract from the policy files distributed with this skill. Use only fresh authoritative runtime inputs and current executable mirrors.

The deterministic daily engine must produce a validated `DecisionPacket` before any Markdown or LLM presentation. The packet is authoritative for runtime status, decision, calculations, eligible channels, blockers, next conditions, and execution authority. A renderer may explain or format those fields; it must not recompute, upgrade, downgrade, omit, or replace them.

Pass every required source as an explicit capability record with `status`, `source`, and endpoint-level `observed_at`. An unavailable source carries `null`, not `0`, `{}`, or `[]`; explicit unavailability is a valid `DecisionPacket` outcome, not permission to invent a value. Keep live last prices separate from the last completed daily close, and derive drawdown only from the latter and its dated ATH close.

Produce the repository-defined daily sections from that packet, clearly separating facts, rule interpretation, candidates, blockers, and next observation conditions. A candidate requires operation-specific owner authorization before execution; it is not standing approval or an order.

If any required state, market input, execution state, or control gate is incomplete, the packet must carry the current fail-closed status and stop new transaction candidates. Never substitute an old report, manual figures, or renderer judgment for the machine decision.

Treat an unavailable alert inventory as `DATA INCOMPLETE`, while an authoritative successful read may legitimately return an empty list. Missing look-through data localizes to the tilt-restore channel. Inspect standing broker automations when the adapter exposes them; an enabled automation that can add an out-of-universe security is a control blocker, but the agent must not change the broker setting.
