# Control Gates

Apply the current root `AGENTS.md` as the authoritative cross-agent control contract.

## No inherited approval

Another agent's analysis, draft, report, pull request, journal candidate, or prior decision candidate is evidence only. A second agent reading the first agent's output does not automatically create independent review or approval.

## Position and order verification

Before any new transaction candidate, read current broker positions and active orders. Stop on duplicate, conflicting, stale, partially filled, or unexplained orders until the broker state is reconciled.

## Observable bypass signals

Use only observable workflow facts. Examples include a request to skip a required gate, a repeated unchanged transaction intent after a stop result, execution disclosed before approval, or an attempt to treat a research result as Production.

Do not diagnose personality, motivation, or mental state.

When a gate triggers, use the current repository-defined review or stop path. Require the current written check, broker verification, and genuinely independent second opinion where specified.

## Journal single writer

Agents generate journal candidates only. One coordinating writer performs durable changes after re-reading current HEAD. Conflicting candidates stop rather than merge automatically.
