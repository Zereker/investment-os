# Codex Action Mapping

Use this only after `using-investment-os` is active.

| Abstract action | Codex mapping | Failure behavior |
|---|---|---|
| Identify policy source | Read `.plugin-version` and report it as the distribution version in effect. A session has no way to prove its distribution is the newest one, and must not imply otherwise. | Stop formal work when the distributed policy files are missing or unreadable. |
| Read policy files | Read the policy files distributed with this skill. | Do not substitute model memory, an earlier checkout, or a copy fetched at runtime. |
| Build Broker Runtime | Use an installed read-only broker capability as an adapter, normalize its output to the `broker-runtime` contract, then run `scripts/broker_runtime.py` for the capabilities required by the task. | No broker capability, unsupported field, stale snapshot, or failed reconciliation means `DATA INCOMPLETE`; pasted values remain context only. |
| Read market state | Use a current market-data capability and preserve source/time metadata in Broker Runtime. | Stop affected calculations on stale or unidentified data. |
| Independent second opinion | Use a separate agent only when multi-agent capability is enabled and the reviewer independently reads authoritative inputs. | Never claim independent review when the capability is absent. |
| Run deterministic tools | Execute current repository scripts in an ephemeral workspace. | Treat script/policy disagreement as a bug or review condition. |
| Change repository | Create a non-default branch, run checks, push, and open a pull request. | Do not merge or push the protected branch without explicit authority. |

A concrete connector such as IBKR is an adapter, not the Investment OS interface. Codex native skill discovery may remove the need for a session hook, but clean-session acceptance tests must prove that relevant skills are actually selected.
