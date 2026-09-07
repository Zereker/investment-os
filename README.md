# Investment OS

## What

Karpathy-rules for long-term investing: one [Agent skill](skills/investment-os/SKILL.md), a constitution plus per-task procedure references, and deterministic fact, math, and execution controls.

```text
Facts → Rules → LLM Judgment → Owner-Authorized Execution
```

This repository is the installable product. It stores rules, never personal portfolio data. This project supports personal discipline; it is not investment advice.

## ChatGPT

Investment OS is packaged as an OpenAI plugin with:

- `.codex-plugin/plugin.json` as the plugin manifest;
- `skills/investment-os/SKILL.md` as the canonical behavior layer;
- `.app.json` declaring the ChatGPT Interactive Brokers app dependency used for authoritative live account state.

The Skill remains usable without a broker connection for policy questions, hypotheticals, research, and audits. Any path that depends on real account state must fail closed with `DATA INCOMPLETE` when an authoritative account capability is unavailable.

The Interactive Brokers app is a runtime dependency only. No IBKR account id, credential, token, portfolio snapshot, order, fill, or authorization record belongs in this repository.

Support, privacy, and usage terms are published in [SUPPORT.md](SUPPORT.md),
[PRIVACY.md](PRIVACY.md), and [TERMS.md](TERMS.md).

### ChatGPT distribution

The repository is structurally compatible with the OpenAI plugin manifest format and can be installed from its marketplace for local or workspace use. That distribution packages the Investment OS skill with a mapping to the existing Interactive Brokers integration.

This repository is not, by itself, a public Plugins Directory release. OpenAI's public submission flow does not accept a new plugin submission that merely references an already-published third-party integration. Public-directory publication therefore requires a separately reviewed distribution plan; a Git tag or GitHub Release does not substitute for that review. Do not describe the repository build as publicly published until the corresponding OpenAI release exists.

Once installed in ChatGPT, start with prompts such as:

- `Daily`
- `Review my monthly funding under Investment OS.`
- `Evaluate this transaction under the current policy.`

If the connected Interactive Brokers app is not authorized, Investment OS still answers non-account-dependent requests and closes only the paths requiring live broker state.

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

Installing the plugin does not by itself give the agent account access. The rules require every account fact to come from an authoritative capability, and pasted figures are context rather than truth, so **without a broker connector every real-money path correctly returns `DATA INCOMPLETE`**. The connector is configured in the host product, never in this repository: no account id, credential, or token belongs here.

For ChatGPT, the plugin manifest declares the Interactive Brokers app dependency. Interactive Brokers exposes account and market capabilities to ChatGPT after the user connects and authorizes the app. The app may expose order-drafting capabilities, but the Investment OS Skill preserves the stricter execution boundary: a recommendation or candidate is never authorization, and final authority remains with the account owner.

`scripts/broker_runtime.py` validates whatever an adapter supplies before any domain rule consumes it. Its required sections map to broker data as follows; `identity`, `snapshot`, `capabilities`, `observations` and `reconciliation` are computed by the adapter rather than fetched.

| Runtime section | Broker source | What it blocks when unavailable |
|---|---|---|
| `account_summary`, `balances`, `positions` | positions, cash balances, margin, multi-currency balances | everything: reconciliation cannot run, so all funding formulas stop |
| `cash_transactions` | historical transactions | the authoritative monthly contribution `F`, which must never be inferred, so Routine DCA stays `DATA INCOMPLETE` |
| `open_orders` | broker open-order capability | all new transaction candidates; the Open Orders gate defaults to `unknown` and only an explicit `clear` proceeds |
| `market_inputs` | prices; the all-time-high close series may need a separate source | drawdown tier evaluation for the day |
| `alert_inventory` | broker-side drawdown alerts, if exposed by the connected capability | the alert pointer consistency check, which forces `Account Health = WARN` and freezes drawdown deployment candidates |
| `standing_automations` | broker-resident automation, if exposed by the connected capability | the daily check for automation that could bypass the Production universe |

Verify each capability against the connected runtime before trusting a formal result: a gap does not degrade the system quietly, it closes the affected path by design.

## Use

Start a new session and say `Daily`, ask for a monthly funding review, evaluate a transaction, research a policy change, or explicitly authorize one broker operation. The Skill loads only the policy files needed for that task.
