---
name: using-investment-os
description: Use when starting any Investment OS portfolio, transaction, research, or system-governance task and the relevant workflow skills must be selected before acting.
---

# Using Investment OS

## Core rule

Investment OS is a composable skill system. Select the required domain skills before analysis or action. The current default-branch HEAD is the only policy authority; skills contain procedure, never investment parameters or portfolio state.

## Route

- Live portfolio or daily status: use `reconstructing-portfolio-state`, `enforcing-behavioral-controls`, then `running-daily-review`.
- Monthly contribution or routine funding: use `reconstructing-portfolio-state`, `enforcing-behavioral-controls`, then `running-monthly-review`.
- Proposed transaction: use `reconstructing-portfolio-state`, `enforcing-behavioral-controls`, then `evaluating-transaction-candidates`.
- New asset, indicator, exception, or policy idea: use `routing-investment-research`.
- Repository, privacy, CI, or production-readiness review: use `auditing-investment-os`.

## Mandatory start

1. Resolve the repository default branch and exact HEAD SHA.
2. Read `AGENTS.md`, `PROJECT.md`, and `PRODUCTION.md` from that SHA.
3. Load only the domain skills required for the task.
4. Never inherit approval from another agent or prior output.
5. Stop when a required authority, runtime source, or control gate is unavailable.

## Completion

Every formal result states the exact rule source, runtime-source health, authority boundary, decision status, and next verifiable observation condition.