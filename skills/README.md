# Investment OS Skills

## Available Skill

- [`investment-os`](investment-os/SKILL.md) — platform-neutral execution and enforcement layer for the current repository policy.

## Distribution Architecture

```text
skills/investment-os/       shared skill source
.claude-plugin/             Claude Code distribution metadata
.codex-plugin/              Codex distribution metadata
repository HEAD             current policy and executable mirrors
broker runtime              current private account state
```

The skill directory is shared verbatim across supported harnesses. Platform-specific manifests discover and distribute it; they do not copy or rewrite the skill body.

The skill is intentionally parameter-free. It contains procedure, routing, controls, and failure behavior. Current policy values remain only in the authoritative repository files and executable mirrors.

## References

The main `SKILL.md` stays concise. Detailed reusable guidance lives in:

- `references/authority-and-runtime.md`
- `references/task-routing.md`
- `references/control-gates.md`

## Runtime Requirements

A production run requires capabilities that can:

- resolve the authoritative repository default branch and current commit;
- read the broker sources required by the current Production contract;
- obtain required market inputs;
- keep real account state ephemeral and private.

Missing repository, broker, or market access is a fail-closed condition. Memory, old reports, screenshots, or manually pasted figures are not substitutes.

## Installation and Validation

See [`docs/SKILL-DISTRIBUTION.md`](../docs/SKILL-DISTRIBUTION.md) for Claude Code and Codex distribution details and clean-session acceptance tests.

Run:

```bash
python3 scripts/check_skill_distribution.py
```

The validator checks frontmatter, trigger-oriented description, references, manifest versions, platform neutrality, and the absence of embedded policy parameters.
