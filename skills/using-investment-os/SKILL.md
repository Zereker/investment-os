---
name: using-investment-os
description: Use when starting any Investment OS portfolio, transaction, research, or system-governance task and the relevant workflow skills must be selected before acting.
---

# Using Investment OS

## Core rule

Investment OS is a composable skill system. Select every required domain skill before analysis or action. The policy files distributed with this skill are the authority for the session that loaded them; skills contain procedure, never investment parameters or portfolio state.

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

1. Read `AGENTS.md`, `PROJECT.md`, and `PRODUCTION.md` as distributed with this skill.
2. State the policy source as the distribution version in `.plugin-version`. Never fetch, or claim to have fetched, a newer policy version at runtime: what shipped is what executes, and whether a distribution is current is a release concern rather than a session one.
3. Load only the domain skills required for the task.
4. For live account work, build and validate the broker-neutral Broker Runtime before portfolio reconstruction.
5. Never inherit approval from another agent or prior output.
6. For a broker write, require current-session authorization bound to one normalized operation and complete authoritative read-back verification.
7. Stop when a required authority, runtime source, review capability, control gate, execution capability, or verification step is unavailable.

## Harness mapping

Use the mapping for the running environment without changing domain skill content:

- Claude Code: `references/claude-code-tools.md`
- Codex: `references/codex-tools.md`

A harness-specific connector is an adapter, not the Investment OS contract. Never simulate a missing broker, market-data, independent-review, repository, execution, or verification capability.

## Completion

Every formal result states the exact rule source, Broker Runtime health, authority boundary, decision status, and next verifiable observation condition. Every broker write additionally states the operation-specific authorization scope, adapter capability, read-back result, and verification status.
