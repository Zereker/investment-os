# Behavior Runtime

Behavior Runtime verifies whether an Agent actually follows Investment OS across turns, reframing, distractions, missing data, and authorization boundaries.

It does not decide investment policy and does not execute Broker operations.

## Components

- `contract/behavior-contract.yaml`: one canonical behavior contract;
- `corpus/`: high-value synthetic adversarial cases used for regression design;
- `replay/`: privacy-safe abstractions of known failure patterns with stable expectations;
- `scripts/behavior_packet.py`: validated result packet for independent verification;
- `evals/run.py`: actor/verifier harness for real clean-session execution.

## Verification boundary

Deterministic CI validates schemas, registration, privacy, packet consistency, and harness integrity. It does not prove model behavior.

A behavior result is verified only when:

1. the Actor runs the complete synthetic scenario in one persistent clean session;
2. an independent Verifier receives the full transcript;
3. the Verifier judges semantic intent continuity rather than keyword overlap;
4. every behavior dimension has non-empty transcript evidence;
5. actor and verifier session identities differ.

Until such a run occurs, the authoritative status remains:

```text
Real Harness behavior: NOT YET VERIFIED
```

Automatic mutation belongs in future fuzz or scheduled suites, not the required PR test path. The required corpus stays small, adversarial, reviewable, and stable.
