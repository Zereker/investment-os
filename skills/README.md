# Investment OS Skills

Investment OS is a composable skill system, not one monolithic skill.

## Skill library

- `using-investment-os` — bootstrap and task router.
- `reconstructing-portfolio-state` — rebuild current broker and market state.
- `enforcing-behavioral-controls` — apply cross-agent and procedural control gates.
- `running-daily-review` — render the current daily decision product.
- `running-monthly-review` — evaluate routine funding and deployment paths.
- `evaluating-transaction-candidates` — evaluate a specific real-money action.
- `routing-investment-research` — keep new ideas outside Production until promoted.
- `auditing-investment-os` — inspect policy, implementation, privacy, CI, and readiness.

## Architecture

```text
skills/*/SKILL.md          platform-neutral composable skills
.claude-plugin/            Claude Code distribution metadata
.codex-plugin/             Codex distribution metadata
repository HEAD            current policy and executable mirrors
broker runtime             current private account state
```

Skills define when and how to perform a reusable capability. They never contain current investment parameters or portfolio state. Policy values remain in authoritative repository files, deterministic calculations remain in `scripts/`, and live state remains ephemeral.

## Testing

- `tests/` validates manifests, package shape, routing, privacy, parameter isolation, and deterministic tools.
- `evals/` defines synthetic pressure scenarios that verify actual agent behavior in clean sessions.

Run the static suite:

```bash
python3 scripts/check_skill_distribution.py
python3 scripts/check_skill_evals.py
```

See [`docs/SKILL-DISTRIBUTION.md`](../docs/SKILL-DISTRIBUTION.md) for harness installation and behavior acceptance testing.