# Investment OS Skill Distribution

Investment OS follows a cross-harness plugin architecture with one shared composable skill library:

```text
skills/*/SKILL.md          platform-neutral skill source
.claude-plugin/            Claude Code distribution metadata
.codex-plugin/             Codex distribution metadata
repository root            authoritative policy and executable mirrors
broker runtime             current private account state
```

## Skill composition

`using-investment-os` is the bootstrap and router. It selects only the domain skills required for the task. Daily, monthly, transaction, research, audit, state-reconstruction, and behavioral-control capabilities remain independently discoverable and testable.

The skills name actions and boundaries rather than vendor-specific tools. Harness manifests distribute the same `skills/` tree without copying or rewriting policy.

## Invariants

1. The repository default-branch HEAD is the only policy authority.
2. Skills contain procedure, never current investment parameters or portfolio state.
3. Deterministic calculations stay in repository scripts.
4. Runtime account state stays private and ephemeral.
5. Another agent or prior output never creates inherited approval.
6. Missing repository, broker, market, or execution-state capabilities fail closed.

## Harness distribution

Claude Code discovers the shared `skills/` directory through `.claude-plugin/plugin.json`. Codex reads `.codex-plugin/plugin.json`, which declares `./skills/` as the skill source. Installation does not grant broker access; missing runtime capabilities must produce a blocking result rather than a simulated account review.

## Testing model

Investment OS uses the same two-layer distinction as mature skill projects:

- `tests/`: non-LLM package, manifest, privacy, routing, and deterministic integration checks.
- `evals/`: synthetic pressure scenarios executed in clean agent sessions to verify actual behavior.

Static PR checks:

```bash
python3 scripts/check_skill_distribution.py
python3 scripts/check_skill_evals.py
```

Behavior acceptance tests should run selected scenarios in each supported harness. A full sweep should use an actor agent and an independent verifier before a skill release or on a scheduled basis. Real account values must never appear in prompts, fixtures, transcripts, or results.

Required behavioral coverage includes:

- pasted figures are not treated as authoritative broker state;
- missing open orders fails closed;
- another agent's output is not inherited approval;
- rewording does not reset an unchanged transaction intent;
- Research cannot enter Production without the current promotion process.
