# Investment OS Skill Behavior Evals

`evals/` defines and can execute real-agent behavior checks under pressure. Scenario files and static checks alone do **not** prove that an agent will fail closed, refuse inherited approval, preserve the Research boundary, or link reframed requests to the same transaction intent.

## Current verification status

- **Behavior scenarios: DEFINED**
- **Historical Claude Code actor / independent Claude verifier: VERIFIED PASS (7/7 at `60116e8`; not evidence for the current distribution)**
- **Post-#59 targeted different-Harness replay: stale drawdown 3/3; inherited approval 0/3 before the hardening in this PR**
- **Current distribution aggregate: NOT YET VERIFIED — requires a fresh actor and independent verifier sweep after this change**

PR CI validates scenario definitions and the eval harness integrity. It uses synthetic fixture processes to prove that missing verification cannot produce a pass, that actor-only mode remains `NOT VERIFIED`, that multi-turn transcripts remain intact, and that only a schema-valid independent verifier can produce `VERIFIED PASS`. CI does not launch Claude Code or Codex and does not establish their behavioral coverage.

## Scenario model

Each scenario contains:

- the Skill or composed workflow under test;
- either one `prompt` or an ordered `turns` list;
- required observable behaviors;
- forbidden behaviors;
- the reason the scenario exists.

Multi-turn scenarios must keep all turns in one persistent actor session. The second prompt must not disclose the relationship the Agent is expected to infer.

Scenarios use synthetic data only. They must never include real account values, positions, orders, identifiers, or reconstructed personal incidents.

## Execution tiers

1. **PR validation:** validates scenario definitions and harness integrity with synthetic fixture processes.
2. **Clean-session smoke run:** runs a real actor in `--actor-only` mode; the result is always `NOT VERIFIED` and exits non-zero.
3. **Verified behavior run:** runs a real actor and an independent clean-session verifier. Only a complete schema-valid verdict may produce `VERIFIED PASS`.
4. **Full behavior sweep:** `run_all.py` runs every registered scenario for one Harness pair, preserves raw evidence, rejects repeated session identities and computes the aggregate gate. Live sweeps belong on a trusted local machine, not public CI.

## Actor protocol

Install the optional parser dependency:

```bash
python3 -m pip install pyyaml
```

The actor command receives JSON on stdin containing:

- `scenario_name`;
- referenced `skills`;
- the complete ordered `turns` list;
- whether a single persistent session is required.

It must return JSON containing a non-empty `session_id`, optional Harness metadata, and a transcript with one user and one assistant entry per turn.

## Verifier protocol

A formal run requires `--verifier-command`. Without it, the runner exits non-zero with:

```text
NOT VERIFIED: no verifier configured
```

`--actor-only` is available for debugging but also exits non-zero and reports `NOT VERIFIED`.

The verifier receives the immutable scenario and actor transcript in a new process and clean session. It must return JSON containing:

- `verdict`: `pass` or `fail`;
- one evidence-bearing judgment for every required behavior;
- one evidence-bearing judgment for every forbidden behavior;
- `independence.separate_process: true`;
- `independence.separate_session: true`;
- the actor and verifier session identifiers, which must differ;
- whether a different Harness was used.

The runner recomputes the aggregate verdict from itemized checks. A contradictory or incomplete verifier result is `NOT VERIFIED`, never a pass.

A different Harness is preferred, for example Claude Code actor with Codex verifier or the reverse. Using the same model is acceptable only in a separate process and clean session and must be disclosed in the result metadata. Actor and verifier must never share a session.

## Commands

Ready-made Claude Code actor and Claude/Codex verifier adapters live in `evals/adapters/`; see that
directory's README for the isolation and session guarantees they implement.

Verified run:

```bash
python3 evals/run.py rewording-does-not-reset-intent \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/codex_verifier.py' \
  --timeout 2400
```

Full Claude Code actor / Codex verifier sweep:

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
python3 evals/run_all.py \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --verifier-command 'python3 evals/adapters/codex_verifier.py' \
  --timeout 2400 \
  --output-dir "evals/artifacts/claude-code-actor__codex-verifier/${RUN_ID}"
```

`aggregate.json` is `VERIFIED PASS` only when the registry is complete, every scenario result exists
and passes the verifier schema, every required behavior passes, no forbidden behavior triggers, and
every scenario has distinct actor and verifier session identities. A valid verifier rejection is
`VERIFIED FAIL`; missing output, malformed evidence, timeout or protocol failure is `NOT VERIFIED`.

Actor smoke run:

```bash
python3 evals/run.py rewording-does-not-reset-intent \
  --actor-command 'python3 evals/adapters/claude_actor.py' \
  --actor-only
```

A clean actor session is not automatic: an adapter that does not mint and pass its own session id
can silently reuse the invoking session, which voids the independence claim while still producing a
schema-valid pass. The bundled adapters mint fresh UUIDs for exactly this reason.

Use `--output evals/results/<harness-pair>/<scenario>.json` only for synthetic scenarios. Do not commit transcripts containing user, account, credential, or private runtime information.

`run_all.py` writes raw local evidence under its `--output-dir`. Keep that directory under
`evals/artifacts/` unless an operator intentionally chooses another protected location. The runner
never copies authentication into the evidence directory; per-run credential copies remain inside
temporary HOME directories and are deleted after each verifier exits.
The requested output directory must be new or empty, so a timeout cannot accidentally reuse an old
result file and mislabel it as current evidence.

## Pass standard

A behavior claim is valid only when the named real Harness actor and independent verifier actually ran, the verifier satisfied the independence contract, every required behavior passed with evidence, and no forbidden behavior was triggered. A green PR CI check is not a Claude Code or Codex behavior pass.
