# Install in Claude Code

Investment OS is packaged as a Claude Code plugin through `.claude-plugin/plugin.json`. Install it once from the repository marketplace; Claude Code then uses its installed plugin copy rather than requiring the user to clone or enter the Investment OS repository.

## Install

In Claude Code, add the marketplace:

```text
/plugin marketplace add Zereker/investment-os
```

Install the plugin:

```text
/plugin install investment-os@investment-os
```

Start a new session after installation. The Claude manifest carries an inline SessionStart bootstrap that activates the `using-investment-os` router. The bootstrap and every selected skill resolve policy files and deterministic scripts from the installed plugin root, not the user's current working directory.

## Development acceptance test

1. Add this repository through the marketplace command above.
2. Install `investment-os@investment-os`.
3. Start a completely new session.
4. Confirm the session-start hook injects `INVESTMENT_OS_BOOTSTRAP` and the `using-investment-os` router.
5. Confirm all domain skills are discoverable.
6. Ask for a live account review without broker access. The result must fail closed rather than simulate account state.
7. Run the synthetic behavior scenarios in `evals/` before release.

This repository marketplace is a direct distribution channel. It is separate from Anthropic's official marketplace and requires its own publication process for an official listing.

## Required runtime capabilities

Installation does not grant GitHub, broker, market-data, or independent-review access. A missing required capability is a blocking condition.
