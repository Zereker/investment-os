# Agent Execution Contract

## Purpose

This contract is the portable enforcement layer for every AI agent that reads or operates Investment OS.

Its primary purpose is not convenience. It reproduces the procedural and behavioral controls that protect decision quality across agents, sessions and tools.

> This contract contains procedure, never investment policy parameters.

No target, threshold, formula, investment-universe member, lifecycle state or data-source ranking may be copied into this file. Every run must resolve those facts from the current repository authority.

## 1. Fresh Rule Source

Before any portfolio interpretation, trading discussion, Daily Brief, review or repository change, the agent must:

1. read the current default-branch `HEAD` of `Zereker/investment-os`;
2. record the exact commit SHA used;
3. read the current product, production, Constitution and applicable Operating System documents from that commit;
4. treat memory, prior chats, summaries and prior-agent outputs as non-authoritative context;
5. restart rule resolution if `HEAD` changes before the final decision.

The agent must never silently use remembered policy values.

## 2. Fresh Runtime State

Personal portfolio state is not stored in the repository. Before producing a current account decision, the agent must reconstruct state from the broker runtime sources required by the current Production contract.

Manual figures, screenshots, pasted tables and prior reports may be used only as leads or context. They are never authoritative account state and cannot independently authorize a transaction.

If authoritative runtime state cannot be obtained or reconciled, the result is `DATA INCOMPLETE`. The agent must not fall back to remembered values, old snapshots or user-entered numbers.

## 3. Source and Authority Declaration

Every formal Daily Brief, transaction-related review, second opinion or decision packet must declare:

```text
Rule Source
- repository
- branch
- commit SHA

Runtime Source
- required broker reads and their status
- market-data reads and their status

Prior Agent Material
- none / context / draft / evidence
- approval inherited: no

Decision Authority
- current agent role
- owner approval status
- human execution boundary
```

Missing source declarations make the output incomplete.

## 4. No Inherited Approval

No approval is inherited from another agent, conversation, draft, report, pull request, Journal candidate, research note or prior `BUY CANDIDATE`.

Another agent's output may be used only as:

- context;
- evidence;
- a draft;
- an independent opinion.

It is never approval.

Agent A drafting and Agent B reading the draft does not satisfy separation of duties. Only the account owner, or an approval mechanism explicitly defined by the current repository rules, can approve a real-money exception or progression.

## 5. Behavioral and Procedural Control Gate

Before producing any new purchase authorization, the agent must check observable process signals. It must not diagnose personality, motivation or mental state.

Gate signals include:

- an asset or action outside the current Production scope;
- repeated requests for the same economic transaction using different wording or rationales;
- disclosure that an order or trade occurred before the required review;
- repeated same-direction purchases, rapid re-entry or same-day reversal;
- a request to skip a required review, data gate, order-book check or second opinion;
- an unchanged request following an earlier `HOLD`, `WAIT`, `REJECT` or `DATA INCOMPLETE`;
- a new candidate that duplicates or conflicts with open orders;
- missing provenance for a claimed approval or completed check.

A changed description does not create a new transaction intent. The agent must link materially identical requests within the available context.

When a signal is present, the agent must switch from ordinary candidate evaluation to a control response:

```text
CONTROL GATE TRIGGERED
Decision: HOLD / REVIEW / REJECT / DATA INCOMPLETE
Required recovery steps:
- reread current repository HEAD
- rebuild broker state
- verify positions, orders and recent activity
- complete the applicable written checklist
- obtain an independent second opinion when required
- obtain explicit owner approval when required
```

The gate does not create permanent prohibitions. It requires the correct process before reconsideration.

## 6. Independent Second Opinion

A second opinion is independent only when the reviewing agent:

1. resolves the same current repository `HEAD` independently;
2. obtains or verifies the same authoritative runtime state independently;
3. forms its factual and rule analysis before reading the first agent's conclusion;
4. declares any material it later received from the first agent;
5. does not treat agreement as transaction approval.

A coordinator may compare conclusions and surface differences. The coordinator does not convert agreement into approval.

## 7. Order and Position Verification

For every transaction-related review, the agent must inspect the authoritative positions and open-order sources required by Production before considering a new candidate.

The agent must identify:

- duplicate orders;
- conflicting directions;
- partial fills;
- unexplained position changes;
- out-of-scope holdings;
- cash or financing conflicts;
- activity that occurred after the last valid review.

Failure to inspect the required order and position sources blocks new authorization.

## 8. Journal Single-Writer Rule

Agents do not directly treat concurrent Journal edits as authoritative.

- An agent may produce a `Journal Candidate`.
- A candidate has no Production authority until reviewed and committed through the repository workflow.
- Only one coordinating writer may prepare a Journal commit at a time.
- The writer must reread `HEAD` immediately before writing.
- Conflicting candidates require human resolution; agents must not silently merge factual claims or decisions.
- Personal account state remains excluded from the public Journal.

## 9. Repository Changes

Agents must not push directly to the protected default branch.

For a repository change, the agent must:

1. reread current `HEAD`;
2. create a branch;
3. declare whether the change affects product behavior, process controls or investment-policy semantics;
4. run the applicable checks;
5. push the branch and open a pull request;
6. leave merge approval to the owner.

A process-control change must not silently modify investment policy.

## 10. Output Boundary

Agents analyze, calculate, explain and enforce gates. They do not place orders, expose broker credentials, persist personal account state or generate an unattended execution chain.

Every actionable output must preserve the human execution boundary defined by the current repository rules.
