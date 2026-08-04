# Investment OS v4 Direction

Investment OS should give the LLM enough freedom to make investment judgments without turning every judgment into code, schemas, gates or new Skills.

## Principle

> Code verifies facts and protects execution. The LLM makes the investment judgment.

## Runtime Boundary

```text
Broker and market tools
→ verified account facts and calculations
→ LLM analysis and decision
→ owner-authorized execution
```

Code remains authoritative for:

- broker data, arithmetic and account reconciliation
- whether required data is available
- whether an order is authorized, submitted and verified

The LLM remains responsible for:

- selecting relevant evidence
- interpreting markets and portfolio context
- comparing alternatives
- recommending `HOLD`, `BUY`, `SELL`, `WAIT` or further research
- explaining uncertainty and changing its conclusion when evidence changes

`DecisionPacket` is simply the structured handoff between analysis and execution. It must keep verified facts separate from the LLM's conclusion, but it should not become a large universal schema.

## Scope Control

This direction does **not** require:

- a new state platform
- a deterministic scoring engine
- a taxonomy for every kind of rule
- more Skills
- exhaustive fields for every possible investment argument

Add structure only when a real failure demonstrates that it is necessary. Prefer improving an existing contract over creating another layer.

## Execution Boundary

Research and recommendations may be autonomous. A real broker write still requires fresh account state, explicit owner authorization for the exact operation, one submission attempt and authoritative read-back verification.
