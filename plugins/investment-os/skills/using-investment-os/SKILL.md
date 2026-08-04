---
name: using-investment-os
description: Use when starting any Investment OS portfolio, transaction, research, or system-governance task and the relevant workflow skills must be selected before acting.
---

# Using Investment OS

## Core rule

Route by user intent and load the smallest workflow that can complete the task. Skills contain procedure, never investment parameters or portfolio state.

Across workflows, use one consistent decision posture: portfolio first, long term first, decision first, evidence over activity, concise by default. This posture shapes presentation and judgment; it never overrides policy, verified facts, or execution controls. The posture and the seven behavior rules are defined in `financial-agent-discipline`; they govern every real-money task.

## Installed distribution root

Resolve packaged files relative to this `SKILL.md`, never relative to the user's current working directory. The plugin root is `../..` from `skills/using-investment-os/`. Verify that `../../.plugin-version`, `references/product-contract.md`, and `references/agent-execution-contract.md` exist before formal work. Resolve deterministic tools from the owning Skill's `scripts/` directory. Do not clone, fetch, or substitute another Investment OS checkout at runtime.

## Route

Choose one primary workflow:

- live portfolio or daily status, including the terse command `Daily` → `running-daily-review`
- monthly contribution or routine funding → `running-monthly-review`
- proposed transaction → `evaluating-transaction-candidates`
- authorized broker write → `execution-runtime`
- new asset, indicator, exception, or policy idea → `routing-investment-research`
- repository, privacy, CI, or production-readiness review → `auditing-investment-os`

Treat `Daily` as a complete request when live account capabilities are available. Do not ask what the user means or require them to restate the workflow; run the ordinary Daily Review. Ask only when a genuinely required account, policy, or capability input cannot be resolved.

Load supporting skills only when the selected workflow needs them. Live account work normally needs `broker-runtime` and `reconstructing-portfolio-state`; transaction work normally needs `enforcing-behavioral-controls`; `validating-drawdown-state` is loaded only when drawdown affects the decision. Do not load every adjacent skill by default and do not create a new skill when an existing workflow can absorb the procedure.

## Mandatory start

1. Read `references/agent-execution-contract.md` and `references/product-contract.md`.
2. Load only the numbered policy references relevant to the task.
3. Establish the policy source from `../../.plugin-version` and the references used.
4. Select one primary workflow and only the supporting capabilities it requires.
5. For live account work, validate broker state before relying on it.
6. Never inherit approval from another agent or prior output.
7. For a broker write, require current-session authorization bound to one normalized operation and complete authoritative read-back verification.
8. Stop only when missing authority, facts, capability, or verification makes the requested conclusion or execution unsafe.

## Policy references

- Constitution: `references/00-constitution.md`
- Operating Manual: `references/01-operating-manual.md`
- Data Contract: `references/02-data-contract.md`
- Journal: `references/03-journal.md`
- Look-through records: applicable `references/records/lookthrough-YYYY-MM-DD.md`

Conflict precedence follows `references/product-contract.md`. When the transition-plan part of `00-constitution.md` conflicts with `01-operating-manual.md`, the operating manual prevails.

## Harness mapping

- Claude Code: `references/claude-code-tools.md`
- Codex: `references/codex-tools.md`

A harness-specific connector is an adapter, not the Investment OS contract. Never simulate a missing broker, market-data, repository, execution, or verification capability.

## Completion

Every formal result states:

- the policy source used;
- Broker Runtime health when live account data is relevant;
- the authority boundary;
- the decision status;
- the next verifiable observation condition.

Every broker write additionally states the exact authorization scope, adapter capability, read-back result, and verification status.
