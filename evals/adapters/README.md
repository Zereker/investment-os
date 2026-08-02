# Eval Harness Adapters

`evals/run.py` is harness-neutral: it validates the protocol, recomputes the verdict and refuses to
report a pass without an independent verifier. It deliberately does not know how to launch an agent.
These adapters are that missing half — the concrete commands that put a **real** Claude Code session
behind `--actor-command` and `--verifier-command`.

## Commands

Verified run (the only kind that can produce `VERIFIED PASS`):

```bash
python3 evals/run.py <scenario> \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/claude_verifier.py' \
  --timeout 2400 \
  --output evals/results/claude-code-actor__claude-code-verifier/<scenario>.json
```

Actor smoke run (debugging only; always exits non-zero and reports `NOT VERIFIED`):

```bash
python3 evals/run.py <scenario> \
  --actor-command 'python3 evals/adapters/claude_actor.py' --actor-only
```

Multi-turn scenarios run several real sessions' worth of turns. Give `--timeout` room: the runner
timeout covers the whole actor command, not one turn.

## Why these adapters satisfy the independence contract

| Contract requirement | How it is met |
|---|---|
| Clean actor session | A fresh UUID is minted per run and passed with `--session-id`. Without it the CLI can reuse the invoking session, which would silently void the whole run. |
| One persistent session across turns | Turn 1 uses `--session-id`; later turns `--resume` that same id. |
| Separate verifier process and session | The verifier is a separate process with its own fresh UUID; the runner rejects a verifier id equal to the actor's. |
| Verifier not contaminated by the system under test | It runs in a neutral temporary directory, so no `CLAUDE.md`, plugin, SessionStart hook or skill is loaded. It judges from the rubric and transcript only. |
| Disclosed harness metadata | Both adapters report model, tooling and isolation in the result JSON. Same harness, different default model — disclosed as `different_harness: false`. |

## Why an eval run cannot touch the real account

Scenarios are synthetic, but that is a property of the text. These adapters make the isolation
structural:

- `--strict-mcp-config` with an empty `--mcp-config` gives both processes **no MCP servers at all**,
  so no broker connector exists in the session to be called;
- the actor is restricted to read-only tools (`Read`, `Grep`, `Glob`, `Skill`); writes, shell and
  network fetches are denied;
- the verifier gets no tools at all.

The actor still loads the Investment OS plugin via `--plugin-dir`, because the plugin — its router
hook, skills and published rules — **is** the system under test.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `EVAL_ACTOR_MODEL` | `claude-sonnet-5` | actor model |
| `EVAL_VERIFIER_MODEL` | `claude-opus-5` | verifier model; differing from the actor strengthens independence |
| `EVAL_ACTOR_TIMEOUT` | `300` | per-turn timeout, seconds |
| `EVAL_VERIFIER_TIMEOUT` | `600` | verifier timeout, seconds |
| `EVAL_PLUGIN_DIR` | repo root | Investment OS plugin root |

## What a result does and does not prove

A `VERIFIED PASS` covers **one scenario, one harness pair, one run**. It is evidence that the
behavior held under that scenario's pressure, not that the system is verified in general. Behavior
claims for other scenarios remain open until they are actually run and recorded.

Results under `evals/results/` are synthetic by construction — the actor has no broker access and no
account figures can enter a transcript. Never point `--output` at a non-synthetic run.
