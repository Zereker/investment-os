# Eval Harness Adapters

`evals/run.py` is harness-neutral: it validates the protocol, recomputes the verdict and refuses to
report a pass without an independent verifier. It deliberately does not know how to launch an agent.
These adapters are that missing half — the concrete commands that put real Claude Code and Codex
sessions behind `--actor-command` and `--verifier-command`.

## Commands

Verified run (the only kind that can produce `VERIFIED PASS`):

```bash
python3 evals/run.py <scenario> \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/claude_verifier.py' \
  --timeout 2400 \
  --output evals/results/claude-code-actor__claude-code-verifier/<scenario>.json
```

Preferred cross-harness run (Claude Code actor, independent Codex verifier):

```bash
python3 evals/run.py <scenario> \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/codex_verifier.py' \
  --timeout 2400 \
  --output evals/results/claude-code-actor__codex-verifier/<scenario>.json
```

The Codex command requires either an authenticated Codex CLI or `OPENAI_API_KEY`. The adapter creates
a new writable HOME for every verifier invocation. In subscription mode it validates the host
`~/.codex/auth.json`, copies it without following links into the throwaway HOME at mode `0600`, and
deletes that copy with the temporary directory. It never inherits host Codex config, plugins, skills,
sessions or rules. In API-key mode it passes only the key and a small environment allowlist.
The allowlist also preserves the managed runtime's `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`,
`NO_PROXY`, `SSL_CERT_FILE`, and `REQUESTS_CA_BUNDLE` values when present, without recording them in
evidence. This keeps the verifier network-capable behind an approved proxy while retaining host-state
isolation.

Full registered sweep (the only command that can produce an aggregate `VERIFIED PASS`):

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
python3 evals/run_all.py \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/codex_verifier.py' \
  --timeout 2400 \
  --output-dir "evals/artifacts/claude-code-actor__codex-verifier/${RUN_ID}"
```

The output directory contains one result plus exact adapter stdout/stderr and Codex JSONL per
scenario, followed by `aggregate.json`. `run_all.py` continues after failures but exits zero only
when every registered scenario is a schema-valid `VERIFIED PASS`, every result file exists and all
actor and verifier session identities are unique across the sweep.
The run directory must be new or empty; stale outputs are rejected rather than overwritten or
mistaken for evidence from the current invocation.

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
| Installed-distribution authority | The actor runs from a disposable copy of the plugin with `.git` and prior eval results excluded. It cannot resolve a repository commit at runtime or learn from recorded answers. |
| Separate verifier process and session | Each verifier is a separate process. Claude verifies the requested fresh UUID; Codex reports a new ephemeral thread id from its JSONL event stream. The runner rejects either id if it equals the actor's. |
| Verifier not contaminated by the system under test | It runs in a neutral temporary directory, so no `CLAUDE.md`, plugin, SessionStart hook or skill is loaded. It judges from the rubric and transcript only. |
| Host-state isolation | The Codex verifier runs under a new HOME/XDG/TMPDIR tree with an allowlisted environment. Only the selected authentication material is seeded; host config and prior sessions are absent. |
| Different harness preferred | `codex_verifier.py` supplies the preferred Claude Code actor / Codex verifier pairing and reports `different_harness: true`. |
| Disclosed harness metadata | Adapters report model, tooling, session identity and isolation in result JSON. Same-harness Claude verification remains available and is disclosed as `different_harness: false`. |

## Why an eval run cannot touch the real account

Scenarios are synthetic, but that is a property of the text. These adapters make the isolation
structural:

- `--strict-mcp-config` with an empty `--mcp-config` gives both processes **no MCP servers at all**,
  so no broker connector exists in the session to be called;
- the actor runs inside a disposable, git-less plugin distribution with prior eval results removed;
- the actor is restricted to read-only tools (`Read`, `Grep`, `Glob`, `Skill`) plus the distribution's
  deterministic Python scripts; direct writes, unrestricted shell and network fetches are denied, and
  any script-side files are confined to the disposable copy;
- the Claude verifier gets no tools at all;
- the Codex verifier runs ephemeral and read-only with user config, project rules, MCP servers and
  web search disabled, and rejects the run if its JSONL trace contains a tool item.

The actor still loads the Investment OS plugin via `--plugin-dir`, because the plugin — its router
hook, skills and published rules — **is** the system under test.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `EVAL_ACTOR_MODEL` | `claude-sonnet-5` | actor model |
| `EVAL_VERIFIER_MODEL` | `claude-opus-5` | verifier model; differing from the actor strengthens independence |
| `EVAL_CODEX_BIN` | `codex` | Codex CLI executable or absolute path |
| `EVAL_CODEX_VERIFIER_MODEL` | `gpt-5.6-sol` | Codex verifier model |
| `EVAL_CODEX_VERIFIER_REASONING_EFFORT` | `medium` | Codex verifier reasoning effort |
| `EVAL_CODEX_AUTH_MODE` | `auto` | `auto`, `subscription`, or `api-key`; auto prefers an explicitly exported API key and otherwise uses Codex login auth |
| `EVAL_CODEX_AUTH_FILE` | Codex login path | optional subscription `auth.json` source override |
| `EVAL_ACTOR_TIMEOUT` | `600` | per-turn timeout, seconds; the turn that runs the deterministic engine can be slow, and a timeout loses the run rather than producing a result |
| `EVAL_VERIFIER_TIMEOUT` | `600` | verifier timeout, seconds |
| `EVAL_CODEX_VERIFIER_TIMEOUT` | `600` | Codex verifier timeout, seconds |
| `EVAL_PLUGIN_DIR` | repo root | Investment OS plugin source copied into the disposable actor distribution |
| `EVAL_EVIDENCE_DIR` | unset | optional local directory for exact adapter/CLI evidence; set automatically by `run_all.py` |

## What a result does and does not prove

A `VERIFIED PASS` covers **one scenario, one harness pair, one run**. It is evidence that the
behavior held under that scenario's pressure, not that the system is verified in general. Behavior
claims for other scenarios remain open until they are actually run and recorded.

Results under `evals/results/` are synthetic by construction — the actor has no broker access and no
account figures can enter a transcript. Never point `--output` at a non-synthetic run.

Live model runs are trusted-local operations, not public CI. `evals/artifacts/` is ignored by Git;
review raw transcripts and logs before sharing them, and never commit or paste authentication files.
