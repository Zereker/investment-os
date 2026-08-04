# Investment OS v4 Architecture Hardening

## Purpose

This document records the next architectural hardening direction identified during source-level review.

The goal is to move Investment OS from a framework of rules and skills into a long-running operational decision system.

## 1. Decision Engine Boundary

Keep the separation:

```
Data Sources
    -> Runtime Adapters
    -> Deterministic Decision Engine
    -> DecisionPacket
    -> Human/Agent Presentation
    -> Optional Execution
```

LLM components must not recompute portfolio state or override deterministic outputs.

## 2. State Persistence

Introduce an explicit investment state layer rather than relying on conversation history.

Recommended future entities:

- portfolio_state
- decision_history
- observation_history
- policy_version
- execution_audit

## 3. Skill Consolidation

Prefer capability-oriented skills over growing numbers of narrow skills.

Core capabilities:

- portfolio-state
- decision-engine
- review
- execution
- governance

Domain checks should become internal modules where possible.

## 4. Evaluation Strategy

Expand evals around behavioral guarantees:

- missing data must produce DATA INCOMPLETE
- unknown broker state must not generate execution actions
- HOLD remains a valid successful decision
- historical decisions must remain auditable

## 5. Personal Policy Isolation

Keep user portfolio rules outside the public engine.

Example private policy:

- SPYM target allocation
- SOXX target allocation
- QQQM growth allocation
- contribution rules

The public repository should provide the operating system, not personal holdings.
