# Investment OS Skill Distribution

Investment OS is distributed as a composable skill library with one router, reusable domain Skills, deterministic repository tools, and thin harness adapters.

```text
skills/using-investment-os/        bootstrap and router
skills/*/                           reusable domain capabilities
hooks/                              Claude Code session bootstrap
.claude-plugin/                     Claude Code distribution metadata
.codex-plugin/                      Codex distribution metadata
.plugin-version                     plugin distribution SemVer only
repository root                     authoritative policy and executable mirrors
broker runtime                      current private account state
```

## Version boundary

The repository default-branch HEAD identifies the current investment policy. The plugin distribution has a separate SemVer read from `.plugin-version` and copied into the harness manifests.

**Plugin distribution version is not an Investment OS policy version.** Policy history belongs in `Decision-Log.md`; defects belong in `BUGLOG.md`; concrete code history belongs in commits and pull requests.

## Invariants

1. The repository default-branch HEAD is the only policy authority.
2. Skill prose describes actions and controls, not broker values or investment parameters.
3. Harness adapters map abstract actions to available tools without rewriting domain Skills.
4. Runtime account state remains private and ephemeral.
5. Missing repository, broker, market, or independent-review capabilities fail closed.
6. Skills declare required sub-skills explicitly; dependency cycles are forbidden.
7. The retired `07-Releases/` directory must not reappear.

## Claude Code

Claude Code uses `.claude-plugin/plugin.json`, discovers `skills/`, and loads `hooks/hooks.json`. The `SessionStart` hook injects the full `using-investment-os` router at startup, clear, and compaction events.

See [`INSTALL-CLAUDE-CODE.md`](INSTALL-CLAUDE-CODE.md) and `skills/using-investment-os/references/claude-code-tools.md`.

## Codex

Codex uses `.codex-plugin/plugin.json`, which declares `./skills/` and intentionally disables repository hooks. Native Skill discovery must be proven with a clean-session acceptance test.

See [`INSTALL-CODEX.md`](INSTALL-CODEX.md) and `skills/using-investment-os/references/codex-tools.md`.

## Testing model

### Non-LLM tests

Run:

```bash
bash tests/run-all.sh
```

The suite executes the Claude bootstrap hook, parses its JSON, discovers Skills, validates frontmatter and manifests, verifies the dependency graph, enforces parameter/privacy isolation, checks version and release governance, and runs deterministic policy tools.

### Agent behavior evals

**Behavior scenarios: DEFINED**

**Behavior execution: NOT YET VERIFIED**

`check_skill_evals.py` validates scenario structure, Skill references, coverage, and privacy. It does not run Claude Code or Codex. `evals/run.py` requires an external clean-session actor command and an independent verifier command. Until a harness sweep has actually run and its synthetic result has been reviewed, CI green must not be described as behavior coverage.

## Release acceptance

Before claiming behavior support for a harness:

1. install from a clean environment through that harness's own mechanism;
2. prove Skill discovery;
3. prove bootstrap or native automatic selection;
4. run the missing-broker fail-closed scenario;
5. run the inherited-approval and Research-isolation scenarios;
6. use an independent verifier;
7. record only synthetic, redacted compliance results.

Installing the plugin does not grant broker or market access and never authorizes trading.
