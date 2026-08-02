# Agent Execution Contract

## Purpose

This contract is the portable enforcement layer for every AI agent that reads or operates Investment OS.

Its primary purpose is not convenience. It reproduces the procedural and behavioral controls that protect decision quality across agents, sessions and tools.

> This contract contains procedure, never investment policy parameters.

No target, threshold, formula, investment-universe member, lifecycle state or data-source ranking may be copied into this file. Every run must resolve those facts from the current repository authority.

## 1. Fresh Rule Source

Before any portfolio interpretation, trading discussion, Daily Brief, review, broker operation or repository change, the agent must establish exactly one rule-source mode:

1. **Installed distribution:** resolve the plugin root from the loaded `using-investment-os` skill, read `.plugin-version` plus the distributed product, production, Constitution and applicable Operating System documents from that root, and record the distribution version and files used. Do not fetch a newer repository copy at runtime.
2. **Source-repository operation:** when auditing or changing the source repository itself, read the current default-branch `HEAD` of `Zereker/investment-os`, record the exact commit SHA, and read the applicable files from that source state before acting.

In either mode, treat memory, prior chats, summaries and prior-agent outputs as non-authoritative context. Restart rule resolution if the selected installed distribution or source `HEAD` changes before the final result.

The default-branch `HEAD` remains the canonical source from which releases are cut. An installed session executes its immutable distributed snapshot; checking whether that snapshot is current belongs to release governance, not the live decision path. The agent must never silently use remembered policy values.

## 2. Fresh Runtime State

Personal portfolio state is not stored in the repository. Before producing a current account decision or executing a broker operation, the agent must reconstruct state from the broker runtime sources required by the current Production contract.

Manual figures, screenshots, pasted tables and prior reports may be used only as leads or context. They are never authoritative account state and cannot independently authorize a transaction.

If authoritative runtime state cannot be obtained or reconciled, the result is `DATA INCOMPLETE`. The agent must not fall back to remembered values, old snapshots or user-entered numbers.

## 3. Source and Authority Declaration

Every formal Daily Brief, transaction-related review, second opinion, decision packet or execution result must declare:

```text
Rule Source
- mode: installed distribution / source repository
- installed distribution version and files used, or repository branch and commit SHA

Runtime Source
- required broker reads and their status
- market-data reads and their status

Prior Agent Material
- none / context / draft / evidence
- approval inherited: no

Decision Authority
- current agent role
- owner approval status
- execution capability and verification status
```

Missing source declarations make the output incomplete.

## 4. No Inherited Approval

No approval is inherited from another agent, conversation, draft, report, pull request, Journal candidate, research note or prior `BUY CANDIDATE`.

Another agent's output may be used only as context, evidence, a draft or an independent opinion. It is never approval.

Only the account owner, or an approval mechanism explicitly defined by current repository rules, can authorize a real-money operation. Owner authorization is valid only for the exact normalized operation in the current session. It never persists to another operation or session.

## 5. Behavioral and Procedural Control Gate

Before producing any new purchase authorization or executing any broker operation, the agent must check observable process signals. It must not diagnose personality, motivation or mental state.

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

When a signal is present, the agent must switch from ordinary candidate evaluation to a control response and stop execution until the required recovery steps are complete.

## 6. Independent Second Opinion

A second opinion is independent only when the reviewing agent resolves the same current repository `HEAD`, verifies authoritative runtime state independently, forms analysis before reading the first conclusion, declares later received material, and does not treat agreement as transaction approval.

A coordinator may compare conclusions and surface differences. Agreement does not itself authorize execution.

## 7. Order and Position Verification

For every transaction-related review or execution, the agent must inspect the authoritative positions and open-order sources required by Production.

The agent must identify duplicate orders, conflicting directions, partial fills, unexplained position changes, out-of-scope holdings, cash or financing conflicts, and activity after the last valid review.

Failure to inspect the required order and position sources blocks new authorization and execution.

## 8. Broker Execution Runtime

An agent may execute a broker capability only when all of the following are true:

1. current repository rules permit the proposed operation;
2. current Broker Runtime before-state is complete and fresh;
3. the running adapter explicitly supports the required capability;
4. the account owner explicitly authorizes the exact normalized operation in the current session;
5. authorization is bound to an operation digest containing all material parameters;
6. the operation is submitted at most once;
7. authoritative broker state is read back after submission;
8. the observed state is compared with the expected state transition;
9. the result is reported as verified, failed, rejected, pending or unknown without embellishment.

A write response or HTTP success is not verification. The agent must not silently retry an operation whose broker outcome is uncertain. It must first prove whether the original operation reached the broker.

Broad standing authorization, such as permission to trade freely for a session, is insufficient. Authorization does not persist in Git, Skill files, logs or future sessions.

Execution receipts are ephemeral. Real account data, order details, broker identifiers, fills and authorization records must not be committed to the public repository.

## 9. Journal Single-Writer Rule

Agents do not directly treat concurrent Journal edits as authoritative.

- An agent may produce a `Journal Candidate`.
- A candidate has no Production authority until reviewed and committed through the repository workflow.
- Only one coordinating writer may prepare a Journal commit at a time.
- The writer must reread `HEAD` immediately before writing.
- Conflicting candidates require human resolution.
- Personal account state and execution receipts remain excluded from the public Journal.

## 10. Repository Changes

Agents must not push directly to the protected default branch.

For a repository change, the agent must reread current `HEAD`, create a branch, declare impact, run applicable checks, push the branch, open a pull request and leave merge approval to the owner.

A process-control change must not silently modify investment policy.

## 11. Output Boundary

Agents may analyze, calculate, explain, enforce gates and execute broker operations under Section 8. They must not expose broker credentials, persist personal account state, invent missing parameters, expand authorization, or create an unattended execution chain.

Every broker operation preserves an explicit owner authorization boundary and authoritative read-back verification. Every non-executed recommendation remains a recommendation, not implied standing permission.
