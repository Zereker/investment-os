# Investment OS Skill Distribution

Investment OS is distributed as a composable skill library with one router, reusable domain Skills, deterministic repository tools, and thin harness adapters.

```text
plugins/investment-os/              complete installable product
  .claude-plugin/                   Claude Code plugin manifest
  .codex-plugin/                    Codex plugin manifest
  .plugin-version                   plugin distribution SemVer only
  skills/using-investment-os/       bootstrap, router, policy references
  skills/*/scripts/                 skill-owned deterministic tools
.agents/plugins/                    Codex repository marketplace
.claude-plugin/marketplace.json     Claude Code repository marketplace
tests/, evals/, Research/           source-only validation and evidence
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

## Release procedure

1. A distribution change (anything under `plugins/investment-os/`) bumps `.plugin-version` and the three manifests in the same PR.
2. After that PR merges, push an annotated tag `v<version>` at the merge commit on the default branch. The tag is the provenance record: auditors resolve version → tag → commit offline.
3. Backfilled: `v0.5.0` and `v0.5.1` are tagged at their introducing merge commits. Versions before 0.5.0 predate the plugin-native layout and were never released as installable distributions (`0.1.0` was never tagged, per Decision-Log 2026-08-02); they intentionally carry no tags.

## Invariants

1. The repository default-branch HEAD is the only policy authority.
2. Skill prose describes actions and controls, not broker values or investment parameters.
3. Harness adapters map abstract actions to available tools without rewriting domain Skills.
4. Runtime account state remains private and ephemeral.
5. Missing repository, broker, market, or independent-review capabilities fail closed.
6. The router names every skill it can route to or load and loads the smallest workflow for the task; where a skill declares a required sub-skill, dependency cycles are forbidden.
7. The retired `07-Releases/` directory must not reappear.

## Claude Code

Claude Code installs `plugins/investment-os`, discovers its `skills/`, and loads the inline SessionStart definition from the nested `.claude-plugin/plugin.json`. The hook runs `skills/using-investment-os/scripts/claude-session-start` and injects the full router at startup, clear, and compaction events.

See [`INSTALL-CLAUDE-CODE.md`](INSTALL-CLAUDE-CODE.md) and `plugins/investment-os/skills/using-investment-os/references/claude-code-tools.md`.

## Codex

Codex installs the `.agents/plugins/marketplace.json` entry, whose source is `./plugins/investment-os`, and uses the nested `.codex-plugin/plugin.json`, which declares `./skills/`. The Codex distribution has no hook field and no default hook path, so native Skill discovery is the only bootstrap. It must be proven with a clean-session acceptance test.

## Installed-runtime boundary

Marketplace installation copies the plugin package into the harness cache. At runtime, `using-investment-os` resolves the plugin root from its own installed path and reads policy files and scripts from that immutable copy. The user's current working directory may be any unrelated project; it is never treated as the Investment OS policy root. Runtime sessions do not clone or update this repository.

See [`INSTALL-CODEX.md`](INSTALL-CODEX.md) and `plugins/investment-os/skills/using-investment-os/references/codex-tools.md`.

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

The stored Claude Code actor / independent Claude verifier sweep is the pre-fix plugin-native run at
product head `6fbf415`: six scenarios `VERIFIED PASS` and `stale-drawdown-alert-tier`
**`VERIFIED FAIL (2/4)`**. A cross-harness Codex-verifier replay of the same transcripts preserved
that failure and surfaced one additional control gap in `no-inherited-agent-approval`. Both findings
were fixed in PR #59 without changing investment policy, but the stored evidence intentionally
remains pre-fix — relabeling it would rewrite history (see `evals/results/README.md`). A fresh actor
sweep on the post-#59 head is still required; the earlier 7/7 sweep at head `60116e8` is superseded
because it described the pre-relayout distribution. The cross-harness claim remains
`NOT YET VERIFIED` until `evals/run_all.py` produces a schema-valid aggregate `VERIFIED PASS` from a
trusted local run.

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
