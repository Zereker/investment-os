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

Three things are easy to conflate and must stay distinct:

| Layer | What it is | Who establishes it |
|---|---|---|
| **Canonical authority** | The default-branch HEAD identifies the current investment policy. Policy changes happen here. | The repository |
| **Session input** | The policy files of the installed distribution. A session reads these and only these; it never fetches a newer copy at runtime. | The installation |
| **Provenance** | Each released `.plugin-version` has a matching Git tag, and that tag is the record of the source commit the distribution was cut from. | The release, at release time |

A session therefore reports the distribution version it is running, never a commit it resolved for itself. An auditor who needs the exact source commit resolves version → tag → commit offline; nothing about that requires the running session to reach a network or a repository.

The distribution can be behind the default branch. That is a release concern, surfaced by comparing versions and tags — not something a session can detect about itself, and not something it should claim to have checked.

The plugin distribution has a separate SemVer read from `.plugin-version` and copied into the harness manifests.

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
