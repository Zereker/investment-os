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
checked per task. Monthly deployment uses current settled available USD cash, not inferred contributions. Missing cash transactions affect optional disclosure only. Pasted figures remain context, not production inputs.

Without code execution, the skill still performs evidence-based account checks
and policy explanation. Monthly deployment arithmetic requires the bundled
helper; its absence closes that path only, not every review.

## Verification

```bash
bash tests/run-all.sh
```

Checks use Python's standard library and synthetic data only. Tests verify the
policy mirrors, reconciliation tolerance, unavailable/stale capabilities,
monthly execution date, settled cash, optional contribution independence, per-ticker tiers and candidate-only
outputs. Static checks do not prove behavior in a live agent or broker session.

Support, privacy and usage terms: [SUPPORT.md](SUPPORT.md),
[PRIVACY.md](PRIVACY.md), [TERMS.md](TERMS.md).
