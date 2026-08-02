# Investment OS Tests

`tests/` verifies non-LLM infrastructure: skill discovery, frontmatter, manifests, references, policy-parameter isolation, privacy boundaries, dependency routing, Claude bootstrap output, and deterministic repository tools.

These tests answer: **does the plugin and repository wiring actually work?**

Run the complete non-LLM suite with:

```bash
bash tests/run-all.sh
```

`tests/test_skill_system.py` executes the Claude session-start hook, parses its JSON output, discovers every Skill, verifies dependency references, rejects cycles, and confirms Claude/Codex manifests distribute one shared Skill tree.

Behavioral compliance belongs in `evals/`, where clean real-agent sessions are tested against synthetic pressure scenarios.
