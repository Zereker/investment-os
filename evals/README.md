# Investment OS Skill Behavior Evals

`evals/` defines and can execute real-agent behavior checks under pressure. Scenario files and static checks alone do **not** prove that an agent will fail closed, refuse inherited approval, or preserve the Research boundary.

## Current verification status

- **Behavior scenarios: DEFINED**
- **Behavior execution: NOT YET VERIFIED**

PR CI runs `python3 scripts/check_skill_evals.py`. That command validates scenario structure, coverage, privacy, and referenced Skill names; it does not launch Claude Code or Codex and does not establish behavioral coverage.

## Model

Each scenario contains:

- the skill or composed workflow under test;
- a synthetic user prompt;
- required observable behaviors;
- forbidden behaviors;
- the reason the scenario exists.

Scenarios use synthetic data only. They must never include real account values, positions, orders, identifiers, or reconstructed personal incidents.

## Execution tiers

1. **PR static validation:** validates scenario definitions only.
2. **Clean-session smoke test:** run selected scenarios in each supported harness.
3. **Full behavior sweep:** run all scenarios with a real actor Agent and an independent verifier. This is slower and belongs in a manual or scheduled distribution-release gate.

## Runner

Install the optional parser dependency:

```bash
python3 -m pip install pyyaml
```

Run one scenario against a CLI that reads a prompt from stdin and prints the complete assistant transcript to stdout:

```bash
python3 evals/run.py manual-figures-are-not-authority \
  --actor-command '<clean-session agent command>' \
  --verifier-command '<independent verifier command>'
```

The verifier receives JSON on stdin containing the scenario and actor transcript. It must exit zero only when every required behavior is visible and no forbidden behavior occurs.

Use `--output evals/results/<harness>/<scenario>.json` only for synthetic scenarios. Do not commit transcripts that contain user, account, credential, or private runtime information.

## Pass standard

A behavior claim is valid only after the scenario was actually executed in the named Harness and every required behavior was visible with no forbidden behavior. A green static CI check is not a behavior pass.
