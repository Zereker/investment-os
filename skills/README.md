# Investment OS Skills

Investment OS is a composable skill library distributed through one plugin.

## Router

- [`using-investment-os`](using-investment-os/SKILL.md) — bootstrap and task router.

## Domain skills

- [`reconstructing-portfolio-state`](reconstructing-portfolio-state/SKILL.md)
- [`validating-drawdown-state`](validating-drawdown-state/SKILL.md)
- [`enforcing-behavioral-controls`](enforcing-behavioral-controls/SKILL.md)
- [`running-daily-review`](running-daily-review/SKILL.md)
- [`running-monthly-review`](running-monthly-review/SKILL.md)
- [`evaluating-transaction-candidates`](evaluating-transaction-candidates/SKILL.md)
- [`routing-investment-research`](routing-investment-research/SKILL.md)
- [`auditing-investment-os`](auditing-investment-os/SKILL.md)

## Architecture

```text
Skills                 procedure, routing, controls and failure behavior
Repository HEAD        current policy and deterministic tools
Broker runtime         current private account state
Harness adapters       discovery, bootstrap and abstract-action mapping
```

Skills are parameter-free and platform-neutral. Claude Code receives the router through the session-start hook. Codex uses native Skill discovery. Harness-specific action mappings live under `using-investment-os/references/` and never rewrite domain Skills.

## Validation

```bash
bash tests/run-all.sh
```

Real-agent behavior scenarios live in `evals/`. Installation and clean-session acceptance requirements are documented in `docs/SKILL-DISTRIBUTION.md`.
