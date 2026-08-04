---
name: using-investment-os
description: Use when starting any Investment OS portfolio, transaction, research, or system-governance task and the relevant workflow skills must be selected before acting.
---

# Using Investment OS

## Core rule

Investment OS is a composable skill system. Select every required domain skill before analysis or action. The policy files distributed with this skill are the authority for the session that loaded them; skills contain procedure, never investment parameters or portfolio state.

## Installed distribution root

Resolve packaged files relative to this `SKILL.md`, never relative to the user's current working directory. The plugin root is `../..` from `skills/using-investment-os/`. Verify that `../../.plugin-version`, `references/product-contract.md`, and `references/agent-execution-contract.md` exist before formal work. Resolve each deterministic tool from the `scripts/` directory of the Skill that owns it. Do not clone, fetch, or substitute another Investment OS checkout at runtime.

## Route

- Every task, before domain work:
  - **REQUIRED SUB-SKILL:** `financial-agent-discipline`
- Live portfolio or daily status:
  - **REQUIRED SUB-SKILL:** `broker-runtime`
  - **REQUIRED SUB-SKILL:** `reconstructing-portfolio-state`
  - **REQUIRED SUB-SKILL:** `validating-drawdown-state`
  - **REQUIRED SUB-SKILL:** `enforcing-behavioral-controls`
  - **REQUIRED SUB-SKILL:** `running-daily-review`
- Monthly contribution or routine funding:
  - **REQUIRED SUB-SKILL:** `broker-runtime`
  - **REQUIRED SUB-SKILL:** `reconstructing-portfolio-state`
  - **REQUIRED SUB-SKILL:** `validating-drawdown-state` when drawdown deployment is in scope
  - **REQUIRED SUB-SKILL:** `enforcing-behavioral-controls`
  - **REQUIRED SUB-SKILL:** `running-monthly-review`
- Proposed transaction:
  - **REQUIRED SUB-SKILL:** `broker-runtime`
  - **REQUIRED SUB-SKILL:** `reconstructing-portfolio-state`
  - **REQUIRED SUB-SKILL:** `validating-drawdown-state` when drawdown funding is claimed
  - **REQUIRED SUB-SKILL:** `enforcing-behavioral-controls`
  - **REQUIRED SUB-SKILL:** `evaluating-transaction-candidates`
- Authorized broker write or trade execution:
  - **REQUIRED SUB-SKILL:** `broker-runtime`
  - **REQUIRED SUB-SKILL:** `reconstructing-portfolio-state`
  - **REQUIRED SUB-SKILL:** `enforcing-behavioral-controls`
  - **REQUIRED SUB-SKILL:** `evaluating-transaction-candidates` when the operation changes financial exposure
  - **REQUIRED SUB-SKILL:** `execution-runtime`
- New asset, indicator, exception, or policy idea:
  - **REQUIRED SUB-SKILL:** `routing-investment-research`
- Repository, privacy, CI, or production-readiness review:
  - **REQUIRED SUB-SKILL:** `auditing-investment-os`

## Mandatory start

1. Read `references/agent-execution-contract.md` and `references/product-contract.md` relative to this skill, and apply the `financial-agent-discipline` rules to the whole session.
2. Load the applicable numbered policy references listed below. Do not load research or repository files as Production authority.
3. Establish the policy source for this session from `../../.plugin-version` plus the references just read, and carry it into every formal result as required by **Completion** below. The runtime rule is simple: what shipped is what executes; whether a distribution is current is a release concern rather than a runtime network lookup.
4. Load only the domain skills required for the task.
5. For live account work, build and validate the broker-neutral Broker Runtime before portfolio reconstruction.
6. Never inherit approval from another agent or prior output.
7. For a broker write, require current-session authorization bound to one normalized operation and complete authoritative read-back verification.
8. Stop when a required authority, runtime source, review capability, control gate, execution capability, or verification step is unavailable.

## Policy references

Apply the numbered authority in this order and load only the files relevant to the task:

- Constitution: `references/00-constitution.md` — IPS, investment universe, target allocation, transition plan, sector-tilt framework, position registry
- Operating Manual: `references/01-operating-manual.md` — daily/weekly/monthly/quarterly/annual workflows, daily report contract, deployment framework, state reconstruction, decision checklist
- Data Contract: `references/02-data-contract.md` — data operations, source registry, quality gate, field dictionary, look-through manual check
- Journal: `references/03-journal.md` — investment journal and lessons learned
- Look-through records: applicable `references/records/lookthrough-YYYY-MM-DD.md` files

## Harness mapping

Use the mapping for the running environment without changing domain skill content:

- Claude Code: `references/claude-code-tools.md`
- Codex: `references/codex-tools.md`

A harness-specific connector is an adapter, not the Investment OS contract. Never simulate a missing broker, market-data, independent-review, repository, execution, or verification capability.

## Completion

Every formal result states, explicitly and by name:

- **the policy source it was decided under** — the distribution version from `.plugin-version` together with the specific policy files or skills relied on;
- Broker Runtime health;
- the authority boundary;
- the decision status;
- the next verifiable observation condition.

A result that does not name its policy source is not a formal result. `Per policy` without saying *which* policy is the exact failure this line exists to prevent: a reader cannot check a claim whose source is unstated. This is easiest to skip precisely when the answer feels obvious — a clear-cut fail-closed reply still has to say what it was decided under.

Every broker write additionally states the operation-specific authorization scope, adapter capability, read-back result, and verification status.
