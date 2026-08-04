# Investment OS v4 Architecture Hardening

## Purpose

This document records the next architectural direction identified during source-level review.

The goal is to move Investment OS from a framework of rules and skills into a long-running, agentic investment decision system.

## 1. LLM-Centric Decision Architecture

Investment decisions cannot be reduced to a fully deterministic code path. Market interpretation, evidence synthesis, regime judgment, exception handling, and trade-off analysis require an LLM to exercise bounded discretion.

Preferred architecture:

```
Data Sources
    -> Runtime Adapters
    -> Evidence and Portfolio State
    -> LLM Decision Agent
    -> DecisionPacket
    -> Policy / Risk Validation
    -> Human Authorization or Optional Execution
```

The LLM may:

- interpret conflicting or incomplete evidence
- select relevant analytical methods
- compare scenarios and opportunity costs
- produce portfolio actions and abstentions
- revise conclusions when new evidence appears
- explain uncertainty and identify missing information

Code should support the LLM rather than attempt to replace its reasoning.

## 2. Guardrails, Not a Deterministic Cage

Deterministic components remain valuable for facts and invariants:

- portfolio and cash reconciliation
- arithmetic and exposure calculations
- schema validation
- stale or missing data detection
- broker capability and order-state checks
- hard allocation, liquidity, and authorization limits
- audit logging and idempotency

These controls validate inputs, permissions, and consequences. They should not encode the entire investment thesis or force every decision through a fixed scoring formula.

The system should distinguish:

- `hard constraints`: cannot be overridden without explicit authorization
- `soft policy`: may be overridden by the LLM with stated evidence and rationale
- `heuristics`: optional tools available to the LLM
- `judgment`: the final synthesis performed by the LLM

## 3. DecisionPacket as an Agent Contract

DecisionPacket should record the LLM's decision rather than merely expose a deterministic engine result.

Recommended fields include:

- decision and proposed action
- evidence references
- assumptions
- confidence and uncertainty
- alternative scenarios
- policy exceptions and justification
- invalidation conditions
- required human authorization
- model, prompt, policy, and data versions

This makes LLM judgment inspectable, reproducible where possible, and accountable without pretending that it is deterministic.

## 4. State Persistence

Introduce an explicit investment state layer rather than relying on conversation history.

Recommended future entities:

- portfolio_state
- decision_history
- observation_history
- thesis_state
- policy_version
- execution_audit

Persistent state should preserve both machine facts and evolving LLM theses.

## 5. Evaluation Strategy

Evals should test decision quality and process discipline, not exact deterministic outputs.

Examples:

- the agent identifies material missing evidence
- the agent does not invent broker or market facts
- recommendations cite supporting evidence
- policy exceptions are explicit and justified
- conclusions change appropriately when inputs change
- HOLD remains a valid successful decision
- execution is blocked when authorization or broker state is uncertain
- historical decisions remain auditable

Scenario and adversarial evals are more important than asserting one exact action for every market state.

## 6. Skill Architecture

Skills should expose capabilities and context to the LLM rather than fragment judgment into many rigid mini-engines.

Core capability groups may include:

- portfolio and broker state
- research and evidence retrieval
- investment analysis
- review and decision synthesis
- policy and risk validation
- execution and audit

The LLM should dynamically compose these capabilities according to the decision context.

## 7. Personal Policy Isolation

Keep user portfolio rules and mandates outside the public engine while allowing the LLM to reason over them at runtime.

Example private policy:

- target and acceptable allocation ranges
- liquidity requirements
- contribution rules
- risk tolerance
- instruments and account constraints
- circumstances requiring human approval

The public repository should provide the agentic operating system, governance model, and audit contracts, not personal holdings.

## Principle

Investment OS should not attempt to make the LLM powerless. It should make the LLM informed, bounded, observable, and accountable.
