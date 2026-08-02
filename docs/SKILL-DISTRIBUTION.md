# Investment OS Skill Distribution

Investment OS follows the same separation used by mature cross-harness skill projects:

```text
skills/investment-os/       platform-neutral skill source
.claude-plugin/             Claude Code distribution metadata
.codex-plugin/              Codex distribution metadata
repository root             authoritative policy and executable mirrors
broker runtime              current private account state
```

## Invariants

1. `skills/investment-os/` is shared verbatim across harnesses.
2. Skill prose describes actions and constraints, not vendor-specific tool names.
3. Harness manifests only discover and distribute the shared skill.
4. Current policy always comes from the repository default-branch HEAD.
5. Runtime account state remains private and ephemeral.
6. Missing repository, broker, or market capabilities fail closed.

## Claude Code

Claude Code plugins discover the repository `skills/` directory by convention through `.claude-plugin/plugin.json`.

For development, add this repository as a local plugin or marketplace source using the current Claude Code plugin mechanism, then install `investment-os`. Confirm that the `investment-os` skill appears and can be explicitly invoked before relying on automatic discovery.

## Codex

Codex reads `.codex-plugin/plugin.json`, which declares `./skills/` as the skill source. Install from the repository or a compatible plugin marketplace, then confirm the skill is listed and loads its full `SKILL.md` content.

## Capability requirements

A production account review additionally requires:

- repository read access;
- broker read access required by current Production rules;
- current market-data access;
- an execution environment that does not persist account state.

Installing the plugin does not grant broker access. Missing runtime capabilities must produce a blocking result rather than a simulated review.

## Acceptance tests

Run:

```bash
python3 scripts/check_skill_distribution.py
```

Then test each harness in a clean session with synthetic or non-account prompts:

1. Ask to audit the Investment OS repository. The skill should load and resolve current HEAD.
2. Ask for a live account review without broker access. The skill should fail closed and identify the missing capability.
3. Present pasted portfolio figures as if authoritative. The skill should treat them only as context.
4. Claim that another agent already approved an action. The skill should refuse inherited approval.

Do not use real account values in distribution tests or transcripts.
