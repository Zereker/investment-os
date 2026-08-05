# Claude actor transcripts at 0.9.6 — half of a cross-harness run

Thirteen actor transcripts, one per registered scenario, produced by a real Claude Code actor
against distribution 0.9.6 at source head `5eca30e`. **Every file reports `NOT VERIFIED` and that
is correct**: these were produced with `--actor-only`, which never claims verification. They are
material awaiting judgment, not results.

This directory exists because no single environment holds both CLIs. A cross-harness run is
therefore a relay: a Claude environment records the transcripts, and a Codex environment judges
them. Splitting the run across time and machines does not weaken independence — it strengthens it,
because the verifier receives answers that were already sealed and cannot influence the system
under test while judging it. The contract's three requirements (separate process, separate
session, different harness) all still hold.

## What was checked before committing

| Check | Result |
|---|---|
| Turn counts match each scenario, including the five-turn `rewording-does-not-reset-intent` | 13/13 |
| Actor session identities unique across the sweep | 13/13 |
| Every file reports `NOT VERIFIED` | 13/13 |
| No broker account identifiers in any transcript | pass |
| All transcripts from one head | `5eca30e` |

## Second half: judging these with Codex

`run.py` requires `--actor-command` and has no replay flag, but it does not need one: the actor
command is only a process that writes actor JSON to stdout, so a command that emits a stored
transcript stands in for a live actor. That path was verified working before these files were
committed — the runner accepted it, produced a verdict, and kept the replayed actor session
distinct from the fresh verifier session.

Run this from the repository root in an environment with an authenticated Codex CLI:

```bash
for f in evals/results/claude-actor-0.9.6__pending-codex-verification/*.json; do
  sc="$(basename "$f" .json)"
  [ "$sc" = "README" ] && continue
  python3 evals/run.py "$sc" \
    --actor-command "python3 -c \"import json,sys; sys.stdout.write(json.dumps(json.load(open('$f'))['actor']))\"" \
    --verifier-command 'python3 evals/adapters/codex_verifier.py' \
    --timeout 2400 \
    --output "evals/results/claude-actor-0.9.6__codex-verifier/${sc}.json"
done
```

That produces thirteen verdicts carrying `different_harness: true` — the first full-registry
cross-harness result for this project. Record it under its own directory and leave these
transcripts unchanged; a judged copy never replaces the material it was judged from.

## What this does and does not license

Nothing here changes the published status. `Current distribution aggregate: NOT YET VERIFIED`
holds until a different verifier harness returns a schema-valid aggregate over the complete
registry. A Claude-side sweep cannot produce that result no matter how many scenarios it covers,
which is why this directory is named for what it is still missing.
