# Reconciliation Runtime Boundary

Investment OS uses one deterministic NAV reconciliation rule across Broker Runtime, Daily Review, and Monthly Execution.

The authoritative check compares current NAV with current cash plus current position market values. A self-declared `reconciliation.status: PASS` is metadata only and cannot replace the calculation.

Monthly Execution must also receive an authoritative open-order result. Only `clear` permits a new candidate; `unknown` and `conflicting` fail closed.

Presentation layers consume the resulting status and may not downgrade a reconciliation failure or order conflict to a warning.
