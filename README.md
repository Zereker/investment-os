# Investment OS

## What

Karpathy-rules for long-term investing: one [Agent skill](skills/investment-os/SKILL.md), three policy references, and deterministic fact, math, and execution controls.

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

## Use

Start a new session and say `Daily`, ask for a monthly funding review, evaluate a transaction, research a policy change, or explicitly authorize one broker operation. The Skill loads only the policy files needed for that task.
