# Investment OS

## What

Karpathy-rules for long-term investing: one [Agent skill](skills/investment-os/SKILL.md), a constitution plus per-task procedure references, and deterministic fact, math, and execution controls.

```text
Facts → Rules → LLM Judgment → Owner-Authorized Execution
```

This repository is the installable product. It stores rules, never personal portfolio data. This project supports personal discipline; it is not investment advice.

## Install

Codex:

```bash
codex plugin marketplace add Zereker/investment-os --ref master
codex plugin add investment-os@investment-os
```

Claude Code:

```text
/plugin marketplace add Zereker/investment-os
/plugin install investment-os@investment-os
```

## Broker runtime

Installing the plugin does not give the agent account access. The rules require every account fact to come from an authoritative capability, and pasted figures are context rather than truth, so **without a broker connector every real-money path correctly returns `DATA INCOMPLETE`**. The connector is configured in your harness, never in this repository: no account id, credential, or token belongs here.

Interactive Brokers publishes an MCP server at `https://api.ibkr.com/v1/api/mcp-public` that AI applications supporting MCP, including Claude Code, can link to an authorized account. Note that it is not a read-only integration — IBKR's model lets the assistant draft an order while the client keeps the final click. That matches this system's boundary, where a candidate is never authorization and the owner places the order, but it means the connector's write surface is real and the rules in `SKILL.md`, not the connector, are what keep it closed.

`scripts/broker_runtime.py` validates whatever an adapter supplies before any domain rule consumes it. Its required sections map to broker data as follows; `identity`, `snapshot`, `capabilities`, `observations` and `reconciliation` are computed by the adapter rather than fetched.

| Runtime section | Broker source | What it blocks when unavailable |
|---|---|---|
| `account_summary`, `balances`, `positions` | positions, cash balances, margin, multi-currency balances | everything: reconciliation cannot run, so all funding formulas stop |
| `cash_transactions` | historical transactions | the authoritative monthly contribution `F`, which must never be inferred, so Routine DCA stays `DATA INCOMPLETE` |
| `open_orders` | not named in IBKR's published capability summary — verify at setup | all new transaction candidates; the Open Orders gate defaults to `unknown` and only an explicit `clear` proceeds |
| `market_inputs` | prices; the all-time-high close series may need a separate source | drawdown tier evaluation for the day |
| `alert_inventory` | broker-side drawdown alerts, likely outside the MCP surface | the alert pointer consistency check, which forces `Account Health = WARN` and freezes drawdown deployment candidates |
| `standing_automations` | broker-resident automation | the daily check for automation that could bypass the Production universe |

Verify each capability against your own connector before trusting a formal result: a gap does not degrade the system quietly, it closes the affected path by design.

## Use

Start a new session and say `Daily`, ask for a monthly funding review, evaluate a transaction, research a policy change, or explicitly authorize one broker operation. The Skill loads only the policy files needed for that task.
