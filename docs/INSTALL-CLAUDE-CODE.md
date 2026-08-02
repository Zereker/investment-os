# Install in Claude Code

Investment OS is packaged as a Claude Code plugin through `.claude-plugin/plugin.json`. The plugin ships the shared `skills/` tree and `hooks/hooks.json`.

## Development acceptance test

1. Add this repository through Claude Code's current local plugin or marketplace development mechanism.
2. Install the `investment-os` plugin.
3. Start a completely new session.
4. Confirm the session-start hook injects `INVESTMENT_OS_BOOTSTRAP` and the `using-investment-os` router.
5. Confirm all domain skills are discoverable.
6. Ask for a live account review without broker access. The result must fail closed rather than simulate account state.
7. Run the synthetic behavior scenarios in `evals/` before release.

The repository is not yet published in an official marketplace, so this document intentionally does not claim a marketplace installation command. Record the exact tested command when a marketplace or stable local-development installation path is published.

## Required runtime capabilities

Installation does not grant GitHub, broker, market-data, or independent-review access. A missing required capability is a blocking condition.
