---
name: running-daily-review
description: Use when the user asks what happened in the live portfolio today, what needs attention, or what actions are currently appropriate.
---

# Running Daily Review

Use fresh authoritative account and market inputs. Load supporting skills only when live positions, controls, or a possible transaction make them necessary.

The review behaves like a restrained long-term CIO:

- start with the portfolio, not the market;
- distinguish durable changes from daily noise;
- state the decision before analysis;
- prefer `HOLD` when no evidence justifies a change;
- mention news only when it changes the thesis, risk, recommendation, or next trigger;
- use the shortest complete explanation.

Keep verified facts separate from LLM judgment. Code remains authoritative for broker state, reconciliation, arithmetic, data availability, authorization, and execution status. The LLM selects relevant evidence, interprets context, compares alternatives, and forms the recommendation.

Default output is a 30-second brief with exactly these headings:

1. `Portfolio` — one-line portfolio state.
2. `Change` — one material change, or `No material change`.
3. `Decision` — `HOLD`, `WAIT`, `BUY`, `SELL`, `RESEARCH`, or `DATA INCOMPLETE`.
4. `Reason` — the shortest sufficient explanation.
5. `Next Trigger` — one specific verifiable condition for reassessment.

Lead with the decision content rather than a preamble. Do not add a market recap, generic education, repeated policy text, exhaustive unchanged facts, or multiple speculative watch items. Expand only when the user asks or a material risk cannot be explained safely in the brief.

`HOLD` is a complete successful result, not a lack of analysis. Missing facts may block a transaction recommendation without blocking useful analysis: label the affected decision `DATA INCOMPLETE`, state what is known, and name only the evidence needed to unblock it.

A recommendation is not execution authority. Any broker write requires exact current-session owner authorization and authoritative read-back verification.
