# Source Repository Entry

This repository develops the Investment OS plugin. Before changing the product,
start from `skills/investment-os/SKILL.md` and read
only the numbered policy references required by the change.

The repository root is both the plugin root and development surface. Runtime
rules, procedures, and deterministic tools live under `skills/investment-os/`.
Do not create a second copy of runtime policy.

Use a branch and pull request, run `bash tests/run-all.sh`, preserve the privacy
boundary, and do not change investment policy inside implementation-only work.

## Language boundary

The repository is English except for the investment policy layer, which is
Chinese. The split follows the reader, not preference:

| Layer | Language | Reader |
|---|---|---|
| `skills/investment-os/SKILL.md`, code, tests, docs | English | the agent |
| `skills/investment-os/references/*` | Chinese | the owner |

Two reasons hold this line. Behavior rules bind through naming the exact
failing phrasing, and the only configuration with a full green sweep is English
rules and scenarios over Chinese policy references. And the owner is the final
authority on their own investment law: policy they cannot read directly is
policy whose interpretation has moved to whoever reads it for them.

Do not translate either layer into the other's language. Status vocabulary
(`DATA INCOMPLETE`, `HOLD`, `WAIT`, `COMPLETED`, `NOT EXECUTED`,
`EXECUTION UNKNOWN`, `VERIFICATION FAILED`, `WARN`, and the five daily fields)
stays English on both sides, because the deterministic scripts print those
strings and the rubrics check them literally.
