---
name: running-daily-review
description: Use when the user asks what happened in the live portfolio today, what needs attention, or what actions are currently appropriate.
---

# Running Daily Review

Use fresh authoritative account and market inputs. Load `reconstructing-portfolio-state` and `enforcing-behavioral-controls` only when the requested review depends on live positions or a possible transaction.

The review is a portfolio decision report, not a general market-news digest. Mention news only when it materially changes the portfolio thesis, policy interpretation, risk, recommendation, or next trigger.

Keep verified facts and calculations separate from LLM judgment. Code remains authoritative for broker state, account reconciliation, arithmetic, data availability, authorization and execution status. The LLM selects relevant evidence, interprets context, compares alternatives and forms the recommendation.

Default output is a 30-second brief with exactly these five headings:

1. `Portfolio` — one-line state summary.
2. `Change` — only material changes since the prior valid review.
3. `Decision` — `HOLD`, `WAIT`, `BUY`, `SELL`, `RESEARCH`, or `DATA INCOMPLETE`.
4. `Reason` — the shortest sufficient explanation, including a blocker when present.
5. `Next Trigger` — one specific verifiable condition for reassessment.

Expand beyond this format only when the user asks for detail or a material risk cannot be explained safely in the brief. Do not add a market recap, generic education, repeated policy text, or a list of unchanged facts.

`HOLD` is a complete successful result. Do not manufacture activity. Missing facts may block a transaction recommendation without blocking useful analysis: label the affected decision `DATA INCOMPLETE`, state what is known, and name only the evidence needed to unblock it.

A recommendation is not execution authority. Any broker write requires exact current-session owner authorization and authoritative read-back verification.
