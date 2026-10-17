# Investment OS

A skill for disciplined long-term investing: canonical behavior, Chinese policy
references, and a dependency-free deterministic helper bundled with the skill.

```text
Authoritative facts → Skill checks → Deterministic arithmetic → Judgment → Owner-authorized execution
```

The repository stores rules and synthetic tests, never personal portfolio data.
Investment OS supports personal discipline; it is not investment advice.

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

The plugin registers one skill and the Interactive Brokers app dependency. No
MCP server is required or registered. See [CHATGPT.md](CHATGPT.md) for host
capability limits. The archived MCP snapshot is in [archive/mcp](archive/mcp).
This repository is not itself a reviewed public ChatGPT Plugins Directory release.

## Use

Ask `Daily`, request a monthly funding review, evaluate a transaction, or research
a policy question. The agent reads only the references needed by the task.
Account checks follow `references/07-runtime-checks.md`; hosts with Python 3.11+
can run `skills/investment-os/scripts/check_runtime.py` using ephemeral JSON on
stdin. No package install, network service or broker credentials are needed by
the helper. Its JSON output is a review result, never execution authorization.

Installing a skill does not grant brokerage access. IBKR remains the authoritative
source of account, order, fill and contribution facts. Available capabilities are
checked per task. Monthly funding first invests confirmed external contributions into positive gaps, then migrates one third of remaining excess USD cash. Missing contribution evidence closes dependent funding arithmetic; it is never inferred or set to zero. Pasted figures remain context, not production inputs.

Without code execution, the skill still performs evidence-based account checks
and policy explanation. Monthly deployment arithmetic requires the bundled
helper; its absence closes that path only, not every review. Use task=monthly for
DCA/baseline and task=drawdown for independent SPYM/QQQM ladders. Drawdown needs
neither contribution evidence nor the monthly execution date. A missing ladder
blocks that ticker only. Holdings use fresh IBKR contract-ID mappings, not display names.

## Verification

```bash
bash tests/run-all.sh
```

Checks use Python's standard library and synthetic data only. Tests verify the
policy mirrors, reconciliation tolerance, unavailable/stale capabilities,
monthly execution date, settled cash, contribution evidence, per-ticker tiers and candidate-only
outputs. Static checks do not prove behavior in a live agent or broker session.

Support, privacy and usage terms: [SUPPORT.md](SUPPORT.md),
[PRIVACY.md](PRIVACY.md), [TERMS.md](TERMS.md).

## CNH funding preparation

For CNH already inside IBKR and explicitly designated for the investment sleeve,
follow `references/08-funding-fx.md`: inspect settlement, review a specific
conversion and its fees in IBKR, verify refreshed balances, then use settled USD
at the fixed monthly review. The helper discloses CNH separately without inferring
contributions, converting balances or authorizing orders. No FX execution tool
is assumed; unsupported broker conversions use the owner-confirmed IBKR route.

## Confirmed CNH contributions

For the explicitly approved CNH-only funding convention, source and allocation
period may be confirmed by the user. Follow section 7 of `08-funding-fx.md`:
IBKR must still evidence selected FX fills, fee currency and USD settlement;
complete private reuse history must prevent counting the same fill again. This
is a mixed evidence path, not independent broker proof of an external deposit.
It preserves contribution-first DCA, subsequent migration and separate order
authorization. Simulations never consume funding records. Section 8 specifies a
versioned private journal and the helper's task=funding_ledger reserve/settle
transitions. The host must atomically save and read back revisions outside the
repository; no database or durable storage is bundled. Without verified private
storage, review remains available but dependent live DCA execution stays closed.
