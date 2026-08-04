---
name: running-daily-review
description: Use when the user asks what happened in the live portfolio today, what needs attention, or what actions are currently appropriate.
---

# Running Daily Review

Use fresh authoritative account and market inputs. Load `reconstructing-portfolio-state` and `enforcing-behavioral-controls` when the requested review depends on live positions or a possible transaction.

The review is a portfolio decision report, not a general market-news digest. Mention news only when it materially changes the portfolio thesis, policy interpretation, risk, or next action. Do not fill the report with headlines that do not change the decision.

Keep verified facts and calculations separate from LLM judgment. Code remains authoritative for broker state, account reconciliation, arithmetic, data availability, authorization and execution status. The LLM selects relevant evidence, interprets the portfolio context, compares alternatives and forms the recommendation.

The result should answer five things:

1. What materially changed?
2. What is the current portfolio state?
3. What does it mean for the portfolio?
4. What is the current recommendation or blocker?
5. What specific condition should be watched next?

`HOLD` is a complete successful result. Do not manufacture activity. If missing facts prevent a responsible transaction recommendation, say `DATA INCOMPLETE` for that decision while still explaining what is known and what evidence is missing.

A recommendation is not execution authority. Any broker write requires an exact current-session owner authorization and authoritative read-back verification.
