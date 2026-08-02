# Codex Action Mapping

Use this only after `using-investment-os` is active.

| Abstract action | Codex mapping | Failure behavior |
|---|---|---|
| Resolve repository HEAD | Use repository-aware git or connected GitHub read capability and record the exact SHA. | Stop formal work when the authoritative commit cannot be proven. |
| Read policy files | Read files from that exact commit. | Do not substitute model memory or an earlier checkout. |
| Read broker state | Use an installed read-only broker capability that satisfies the current Production contract. | No broker capability means `DATA INCOMPLETE`; pasted values remain context only. |
| Read market state | Use a current market-data capability and preserve source/time metadata. | Stop affected calculations on stale or unidentified data. |
| Independent second opinion | Use a separate agent only when multi-agent capability is enabled and the reviewer independently reads authoritative inputs. | Never claim independent review when the capability is absent. |
| Run deterministic tools | Execute current repository scripts in an ephemeral workspace. | Treat script/policy disagreement as a bug or review condition. |
| Change repository | Create a non-default branch, run checks, push, and open a pull request. | Do not merge or push the protected branch without explicit authority. |

Codex native skill discovery may remove the need for a session hook, but clean-session acceptance tests must prove that relevant skills are actually selected.
