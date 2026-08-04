# Investment OS

Karpathy-rules for long-term investing: one Agent skill, a small policy set, and fresh runtime facts.

```text
Facts → Rules → LLM Judgment → Owner-Authorized Execution
```

**Code verifies facts and protects irreversible actions. The LLM makes the investment judgment.**

## Use

Install with Codex:

```bash
codex plugin marketplace add Zereker/investment-os --ref master
codex plugin add investment-os@investment-os
```

Or with Claude Code:

```text
/plugin marketplace add Zereker/investment-os
/plugin install investment-os@investment-os
```

Start a new session, then use:

```text
Daily
```

The normal result is a short portfolio decision:

```text
Portfolio
Change
Decision
Reason
Next Trigger
```

`HOLD` is a complete successful decision. Daily Review is not a news digest and does not manufacture activity.

## Rules

- Portfolio first; headlines are secondary.
- Long term first; separate durable change from daily noise.
- Decision first; explain only what matters.
- Never guess account, order, market, or authorization state.
- User-pasted figures and prior Agent output are context, not authority.
- Research never silently becomes Production policy.
- A recommendation is never execution authorization.
- Broker writes require explicit current-session authorization for one operation and authoritative read-back verification.
- Missing facts stop only the affected path.
- Keep the answer as short as the decision allows.

## Product

The complete installable product is [`plugins/investment-os/`](plugins/investment-os/).

- [`using-investment-os/SKILL.md`](plugins/investment-os/skills/using-investment-os/SKILL.md) — the only discoverable Agent skill
- [`references/`](plugins/investment-os/skills/using-investment-os/references/) — current investment policy and execution boundaries
- `skills/*/scripts/` — internal deterministic fact, math, and execution-safety tools

The repository stores rules, never a personal portfolio. Real account identifiers, balances, positions, orders, fills, authorization, and execution receipts remain private and ephemeral.

This project supports personal long-term investment discipline. It is not investment advice and does not guarantee returns.
