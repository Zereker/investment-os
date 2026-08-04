# Investment OS Skill Distribution

Investment OS ships as one **single canonical Skill** plus internal policy references and a small set of deterministic tools.

```text
plugins/investment-os/                     complete installable product
  .plugin-version                          Plugin distribution version
  .claude-plugin/                          Claude Code manifest and bootstrap
  .codex-plugin/                           Codex manifest
  skills/using-investment-os/SKILL.md      the only discoverable Agent skill
  skills/using-investment-os/references/   policy and execution authority
  skills/*/scripts/                        internal deterministic tools
tests/, evals/, Research/                  source-only validation and evidence
```

The historical workflow directories may retain scripts or reference assets, but they must not contain another `SKILL.md`. Users and Harnesses see one Agent, not a skill graph.

## Version boundary

| Layer | Meaning | Established by |
|---|---|---|
| **Canonical authority** | Default-branch HEAD identifies current investment policy. | Repository |
| **Session input** | The immutable files copied into the installed distribution. | Installation |
| **Provenance** | Version tag resolves a distribution version to its source commit. | Release |

A running session reports its installed distribution version. It does not fetch the repository or claim to have checked a newer HEAD.

**Plugin distribution version is not an investment policy version.** Policy history belongs in `Decision-Log.md`; defects belong in `BUGLOG.md`.

## Release procedure

1. Any change under `plugins/investment-os/` bumps `.plugin-version` and every manifest in the same PR.
2. After merge, create annotated tag `v<version>` at the merge commit.
3. Runtime sessions never create or resolve tags.

## Invariants

1. Only `skills/using-investment-os/SKILL.md` is discoverable.
2. The canonical Skill contains behavior and procedure, never portfolio-specific parameters.
3. Numbered references contain current investment policy.
4. Internal scripts verify facts, arithmetic, and irreversible execution boundaries; they do not own investment judgment.
5. Runtime account state remains private and ephemeral.
6. Missing facts or capabilities stop only the affected path.
7. Research, prior output, and another Agent never silently become Production authority.

## Claude Code

Claude Code installs `plugins/investment-os`, discovers the single Skill, and runs `skills/using-investment-os/scripts/claude-session-start` from the nested manifest. The hook injects the installed Skill after startup, clear, and compaction.

## Codex

Codex installs the same plugin and discovers `./skills/` natively. There is no Codex hook field and no second bootstrap contract.

## Installed-runtime boundary

Marketplace installation copies the plugin into the Harness cache. The canonical Skill resolves all references and scripts from that installed copy, never from the user's current working directory. Runtime sessions do not clone, fetch, or update the source repository.

## Testing model

Static checks run with:

```bash
bash tests/run-all.sh
```

They verify the single-skill distribution, policy references, manifests, privacy boundary, internal deterministic tools, and eval-harness integrity.

### Agent behavior evals

**Behavior scenarios: DEFINED**

**Behavior execution: NOT YET VERIFIED**

A green static suite is not proof of real Agent behavior. Behavior claims require a clean-session actor, an independent verifier, synthetic inputs, and stored evidence. Existing scenario `skills` lists are historical coverage labels; the Harness loads the whole plugin and therefore exercises the one canonical Skill.

The last stored full sweep predates this single-skill consolidation and remains historical evidence only. A fresh sweep is required before claiming behavior coverage for the new distribution.

Installing the plugin never grants broker access and never authorizes a transaction.
