# Source Repository Entry

This file governs work on the Investment OS source repository. Before changing
the product, read the installed-product contract at
`plugins/investment-os/skills/using-investment-os/references/agent-execution-contract.md`
and route the task through
`plugins/investment-os/skills/using-investment-os/SKILL.md`.

The repository root is the development surface, not the installed runtime.
Runtime policy, procedures, and deterministic tools must live under
`plugins/investment-os/`. Tests, evals, release checks, research, and governance
history remain outside the plugin. Do not create a second copy of runtime policy.

Do not push directly to the protected default branch. Use a branch and pull
request, run `bash tests/run-all.sh`, preserve the privacy boundary, and do not
change investment policy as part of implementation-only work.
