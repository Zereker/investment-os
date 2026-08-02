# Claude Code Action Mapping

Use this only after `using-investment-os` is active.

| Abstract action | Claude Code mapping | Failure behavior |
|---|---|---|
| Identify policy source | Read `.plugin-version` and report it as the distribution version in effect. A session has no way to prove its distribution is the newest one, and must not imply otherwise. | Stop formal work when the distributed policy files are missing or unreadable. |
| Read policy files | Read the policy files distributed with this skill, not a cached summary, a recalled version, or a copy fetched at runtime. | Treat missing required files as rule-source incomplete. |
| Build Broker Runtime | Use an installed read-only broker integration as an adapter, normalize its output to the `broker-runtime` contract, then run `scripts/broker_runtime.py` for the capabilities required by the task. | No broker capability, unsupported field, stale snapshot, or failed reconciliation means `DATA INCOMPLETE`; pasted values remain context only. |
| Read market state | Use a current market-data capability required by the current workflow and preserve source/time metadata in Broker Runtime. | Stop affected calculations when freshness or source identity cannot be established. |
| Independent second opinion | Use a genuinely independent subagent only when it can read the same authoritative inputs without first receiving the draft conclusion. | Never simulate independence; report the capability as unavailable. |
| Run deterministic tools | Execute the repository scripts at the resolved commit with synthetic or ephemeral inputs. | Treat tool/policy disagreement as a bug or review condition. |
| Change repository | Work on a non-default branch, run checks, and open a pull request. | Never infer permission to merge or push the protected branch. |

A concrete connector such as IBKR is an adapter, not the Investment OS interface. Do not name or depend on an optional tool unless it is actually available in the running environment.
