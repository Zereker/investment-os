# Investment OS Tests

`tests/` verifies non-LLM infrastructure: skill package shape, frontmatter, manifests, references, policy-parameter isolation, privacy boundaries, routing declarations, and deterministic repository tools.

These tests answer: **does the plugin and repository wiring work?**

Run the current deterministic suite with:

```bash
python3 scripts/check_policy_consistency.py
python3 scripts/check_product_contract.py
python3 scripts/check_skill_distribution.py
python3 scripts/check_skill_evals.py
python3 scripts/daily_brief.py --self-test
python3 scripts/alert_pointer_check.py --self-test
```

Behavioral compliance belongs in `evals/`, not in static package tests.