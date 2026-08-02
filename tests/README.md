# Investment OS Tests

`tests/` verifies non-LLM infrastructure: skill discovery, frontmatter, manifests, references, policy-parameter isolation, privacy boundaries, dependency routing, Claude bootstrap output, release governance, and deterministic repository tools.

These tests answer: **does the plugin and repository wiring actually work?**

Run the complete non-LLM suite with:

```bash
bash tests/run-all.sh
```

`tests/test_skill_system.py` executes the Claude session-start hook, parses its JSON output, discovers every Skill, verifies dependency references, rejects cycles, and confirms Claude/Codex manifests distribute one shared Skill tree and version.

Behavior scenarios and the optional real-agent runner live in `evals/`. PR CI validates scenario definitions only; behavioral compliance remains unverified until clean sessions are actually executed and independently checked.
