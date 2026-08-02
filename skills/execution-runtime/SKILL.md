---
name: execution-runtime
description: Use when an authorized broker write, alert change, order placement, order modification, order cancellation, or other broker-side action must be executed and verified.
---

# Execution Runtime

## Goal

Execute one specifically authorized broker operation through a concrete adapter, then read back authoritative broker state and verify the result. Authorization is runtime-only and never persists across operations or sessions.

The only valid authorization scope is `single-operation-current-session`.

## Required inputs

- exact repository HEAD and applicable Production rules;
- validated Broker Runtime before-state;
- one normalized operation request;
- the exact broker capability required by that operation;
- explicit account-owner authorization for that exact operation in the current session;
- a broker adapter that supports execute and read-back for the capability.

Broad authorization such as “trade for me today” is insufficient. The authorization must identify the operation and its material parameters.

## Lifecycle

1. `PREPARED`: normalize the operation and expected state transition.
2. `CAPABILITY_CHECKED`: confirm the adapter supports the required capability.
3. `AUTHORIZED`: bind current-session owner authorization to the normalized operation digest.
4. `EXECUTED`: submit exactly that operation once.
5. `READ_BACK`: read back authoritative broker state; never trust the write response alone.
6. `VERIFIED`: compare observed state with the expected transition and current policy.
7. `COMPLETED`: return an ephemeral execution receipt.

Any missing capability, authorization mismatch, stale before-state, adapter error, ambiguous broker response, or failed read-back produces `NOT EXECUTED`, `EXECUTION UNKNOWN`, or `VERIFICATION FAILED`. Never retry a potentially submitted operation without first proving whether it reached the broker.

## Capability namespace

Examples include:

- `Broker.Write.Alert.Create`
- `Broker.Write.Alert.Modify`
- `Broker.Write.Alert.Delete`
- `Broker.Trade.PlaceOrder`
- `Broker.Trade.ModifyOrder`
- `Broker.Trade.CancelOrder`

Capabilities describe adapter functions, not standing permission. Every write still requires operation-specific current-session authorization.

## Verification

Verification is operation-specific and uses authoritative read-back. For an order, compare side, instrument, quantity, order type, limit or stop terms, time in force, account, order identity, and broker status. For an alert, compare instrument, condition, threshold, status, and uniqueness constraints required by policy.

A broker acknowledgement is not verification. Partial fills, pending review, replacement, rejection, duplication, and cancellation-pending states must be reported exactly.

## Privacy and audit boundary

Return an ephemeral receipt with operation digest, capability, authorization scope, timestamps, adapter, broker identifiers needed by the owner, read-back result, and verification status. Do not commit real account data, orders, fills, broker identifiers, or authorization records to the public repository.

## Prohibitions

- no unattended execution chain;
- no authorization inheritance from another agent, prior message, prior candidate, or earlier operation;
- no parameter completion by guesswork;
- no silent retry;
- no claim of success before authoritative read-back;
- no expansion from the authorized operation to related operations.
