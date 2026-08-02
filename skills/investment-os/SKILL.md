---
name: investment-os
description: Run the current Investment OS repository policy against fresh broker state for daily reviews, monthly funding reviews, research routing, and system audits. Use when the user asks what happened in the portfolio, what is currently authorized, what needs attention, or whether the system itself is healthy.
---

# Investment OS Skill

## Purpose

Operate Investment OS as a portable enforcement and execution layer.

The repository is the only policy authority. This skill contains procedure, routing, safety controls, and failure behavior; it never contains investment policy parameters or portfolio state.

The primary goal is to prevent stale rules, stale account state, implicit approval, and procedural bypass from influencing a real-money decision. Convenience is secondary.

## Required Capabilities

A production run requires:

- GitHub read access to the authoritative repository and its default branch;
- broker read access for the account sources required by the current repository contract;
- market-data access required by the current repository contract;
- an ephemeral execution environment that does not persist personal account state.

A missing required capability is a blocking condition. Do not replace it with memory, an old report, a screenshot, or manually pasted figures.

## Mandatory Cold Start

For every formal run:

1. Resolve the repository default branch at runtime.
2. Read its current HEAD and record the exact commit SHA.
3. Read `AGENTS.md` before processing any investment request.
4. Read `PROJECT.md` and `PRODUCTION.md`.
5. Read only the current policy and workflow files required for the requested task.
6. Treat chat history, prior agent summaries, cached extracts, branches, pull requests, and Research as non-authoritative unless the current default-branch rules explicitly promote them.

Never reuse a policy summary from a prior run without resolving current HEAD again.

## Task Routing

### Daily Review

Use for requests about today, current allocation, current risk, current orders, current drawdown state, permitted actions, or the next observation condition.

Read the current daily workflow and report contract from the repository. Reconstruct broker state, verify market inputs, run the repository's current deterministic calculation tools where available, and render the required daily product.

### Monthly Review

Use for contribution allocation, routine funding, strategic cash migration, drawdown deployment, or routine restoration paths.

Read the current monthly workflow, deployment framework, relevant Constitution files, and executable calculation contract. Do not infer missing contribution, lifecycle, reserve, or executed-state inputs.

### Research Request

Use for a new asset, indicator, strategy, exception, threshold, or policy change.

Route the request to the repository's Research process. Do not let a research result affect Production until the repository's current approval and release process is complete.

### System Audit

Use for repository health, policy drift, privacy, CI, release consistency, or operational readiness.

Inspect current HEAD, open changes, required checks, executable mirrors, product contracts, and privacy controls. Do not use account state unless the audit explicitly requires a runtime production test.

## Runtime State Reconstruction

For a transaction-related or portfolio-related run:

1. Read every broker source required by the current repository contract.
2. Verify timestamps, timezone, currency basis, account identity consistency, and reconciliation.
3. Read current positions and active orders from the broker; do not infer them from prior reports.
4. Treat manual figures, screenshots, pasted tables, and previous outputs only as non-authoritative context.
5. Reconstruct any state that cannot be inferred from market prices using the current repository procedure.
6. If a required source is missing, stale, contradictory, or not reconcilable, return `DATA INCOMPLETE` and stop new transaction candidates.

Never write runtime account state into the repository, Issues, pull requests, fixtures, screenshots, debug logs, or durable output files.

## Source and Authority Declaration

Every formal decision output must declare:

```text
Rule Source
Repository: <repository>
Branch: <resolved default branch>
Commit: <exact HEAD SHA>

Runtime Source
Broker inputs: <PASS / WARN / DATA INCOMPLETE by source>
Market inputs: <PASS / WARN / DATA INCOMPLETE>

Authority
Prior agent output inherited as approval: NO
Current agent may execute trades: NO
Final execution authority: account owner
```

Do not issue a formal decision without an exact repository commit SHA.

## Control Gates

Apply `AGENTS.md` in full. In particular:

- no approval is inherited from another agent, conversation, draft, report, pull request, journal candidate, or prior decision candidate;
- a different agent reading a draft does not automatically satisfy independent review;
- current broker positions and open orders must be checked before a new transaction candidate;
- observable procedural or behavioral bypass signals move the result to the repository-defined review or stop path;
- changing wording does not create a new transaction intent when the underlying requested action is unchanged;
- agents produce journal candidates only; the repository's single-writer process controls durable journal changes.

Do not diagnose personality, motivation, or mental state. Apply only observable workflow signals and repository-defined controls.

## Deterministic Tools

Prefer the repository's current executable mirrors over hand calculations.

Before invoking a tool:

1. Confirm it exists at the resolved commit.
2. Read its documented input contract and hard boundaries.
3. Supply only fresh, authoritative runtime inputs.
4. Treat any disagreement between executable output and current policy as a bug or `REVIEW`, not permission to choose a preferred answer.
5. Keep all real account inputs in memory or standard streams only, unless the repository explicitly defines another private runtime mechanism.

Never copy parameters from the tool into this skill.

## Decision Behavior

Use only the current repository's controlled vocabulary and output contract.

A candidate means the current rules permit human review. It is not an order, approval, or instruction to execute.

Never:

- place or modify an order;
- generate a directly executable order payload;
- invent a missing input;
- use Research as Production;
- expand the Production universe;
- treat price movement, news, or model preference as an unregistered rule;
- bypass a required second opinion, written check, position check, or order-book check;
- continue after a fail-closed condition.

## Privacy

The public repository stores knowledge, never portfolio state.

Keep broker credentials, account identifiers, balances, values, quantities, costs, orders, fills, contributions, returns, tax information, and any derivable personal asset information outside the repository.

Use synthetic data for tests. Clearly label synthetic examples. Never construct examples from rounded real account values.

## Write Boundary

For repository changes:

1. Re-read current default-branch HEAD immediately before writing.
2. Create a non-default branch.
3. Change only files within the approved scope.
4. Run the repository's current required checks.
5. Push the branch and open a pull request.
6. Do not merge or push directly to the protected default branch unless the account owner explicitly requests that exact action and repository governance permits it.

For journals, follow the single-writer contract in `AGENTS.md`.

## Failure Modes

Return a clear blocking result when:

- the authoritative repository or exact HEAD cannot be resolved;
- required policy files cannot be read;
- broker access is unavailable or interactive authorization is incomplete;
- account sources do not reconcile;
- required market data or execution-state data is missing;
- another agent's approval is the only claimed authorization;
- the request requires a Production rule that does not exist at current HEAD.

State what is known, what is missing, why no new candidate is allowed, and the concrete recovery condition.

## Completion Standard

A successful run is not defined by producing a transaction.

It is successful when it:

- uses the exact current repository policy;
- uses fresh authoritative runtime state;
- applies all required control gates;
- produces a reproducible and explainable result;
- preserves privacy;
- states the next verifiable observation condition;
- leaves final execution to the account owner.
