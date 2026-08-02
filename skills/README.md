# Investment OS Skills

## Available Skill

- [`investment-os`](investment-os/SKILL.md) — portable execution and enforcement layer for the current repository policy.

## Architecture

```text
Skill: procedure, routing, controls, failure behavior
Repository HEAD: current policy and executable mirrors
Broker runtime: current private account state
```

The skill is intentionally parameter-free. It must be installed or loaded together with capabilities that can:

- read the authoritative GitHub repository and resolve its current default-branch commit;
- read the broker sources required by the current Production contract;
- obtain the market inputs required by the current Production contract;
- keep real account state ephemeral and private.

The skill does not include broker credentials, portfolio state, target allocations, security identifiers, thresholds, formulas, or executable orders.

## Use

Invoke the skill for:

- daily portfolio and risk reviews;
- monthly funding reviews;
- routing new ideas into Research;
- auditing repository, privacy, and Production readiness.

Every formal run must identify the exact repository commit used. Missing repository or broker access is a fail-closed condition, not a reason to use memory or manually pasted figures.
