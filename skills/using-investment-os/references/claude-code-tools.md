# Claude Code Action Mapping

Use this only after `using-investment-os` is active.

| Abstract action | Claude Code mapping | Failure behavior |
|---|---|---|
| Resolve repository HEAD | Use repository-aware git or GitHub read capability and record the exact SHA. | Stop formal work when the authoritative commit cannot be proven. |
| Read policy files | Read files from the resolved commit, not a cached summary or unmerged branch. | Treat missing required files as rule-source incomplete. |
| Read broker state | Use an installed, read-only broker integration that can return every source required by current Production rules. | No fallback to pasted figures; return `DATA INCOMPLETE`. |
| Read market state | Use a current market-data capability required by the current workflow. | Stop affected calculations when freshness or source identity cannot be established. |
| Independent second opinion | Use a genuinely independent subagent only when it can read the same authoritative inputs without first receiving the draft conclusion. | Never simulate independence; report the capability as unavailable. |
| Run deterministic tools | Execute the repository scripts at the resolved commit with synthetic or ephemeral inputs. | Treat tool/policy disagreement as a bug or review condition. |
| Change repository | Work on a non-default branch, run checks, and open a pull request. | Never infer permission to merge or push the protected branch. |

Do not name or depend on an optional tool unless it is actually available in the running environment.
