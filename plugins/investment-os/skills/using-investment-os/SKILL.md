---
name: using-investment-os
description: Use when starting any Investment OS portfolio, transaction, research, or system-governance task and the relevant workflow skills must be selected before acting.
---

# Using Investment OS

## Core rule

Investment OS is a composable skill system. Select every required domain skill before analysis or action. The policy files distributed with this skill are the authority for the session that loaded them; skills contain procedure, never investment parameters or portfolio state.

## Installed distribution root

Resolve packaged files relative to this `SKILL.md`, never relative to the user's current working directory. The plugin root is `../..` from `skills/using-investment-os/`. Verify that `../../.plugin-version`, `references/project-contract.md`, `references/production-contract.md`, and `references/agent-execution-contract.md` exist before formal work. Resolve each deterministic tool from the `scripts/` directory of the Skill that owns it. Do not clone, fetch, or substitute another Investment OS checkout at runtime.

## Route

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

1. Read `references/agent-execution-contract.md`, `references/project-contract.md`, and `references/production-contract.md` relative to this skill.
2. Load the applicable numbered policy references listed below. Do not load research or repository files as Production authority.
3. Establish the policy source for this session from `../../.plugin-version` plus the references just read, and carry it into every formal result as required by **Completion** below. The runtime rule is simple: what shipped is what executes; whether a distribution is current is a release concern rather than a runtime network lookup.
4. Load only the domain skills required for the task.
5. For live account work, build and validate the broker-neutral Broker Runtime before portfolio reconstruction.
6. Never inherit approval from another agent or prior output.
7. For a broker write, require current-session authorization bound to one normalized operation and complete authoritative read-back verification.
8. Stop when a required authority, runtime source, review capability, control gate, execution capability, or verification step is unavailable.

## Policy references

Apply the numbered authority in this order and load only the files relevant to the task:

- IPS: `references/00-investment-policy-statement.md`
- Constitution: `references/01-investment-universe.md`, `references/01-target-allocation.md`
- Operating System: `references/02-annual-review.md`, `references/02-daily-report-contract.md`, `references/02-daily-review.md`, `references/02-decision-checklist.md`, `references/02-deployment-framework.md`, `references/02-monthly-workflow.md`, `references/02-quarterly-workflow.md`, `references/02-state-reconstruction.md`, `references/02-weekly-review.md`
- Transition: `references/03-transition-plan.md`
- Alpha controls: `references/04-alpha-framework.md`, `references/04-position-registry.md`
- Journal: `references/05-investment-journal.md`
- Lessons: `references/06-lessons-learned.md`
- Data contract: `references/08-data-operations.md`, `references/08-data-registry.md`, `references/08-data-dictionary.md`, `references/08-data-quality.md`, `references/08-lookthrough-check.md`, and applicable `references/08-YYYY-MM-DD-lookthrough-check.md` records

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
