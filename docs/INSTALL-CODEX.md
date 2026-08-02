# Install in Codex

Investment OS is packaged through `.codex-plugin/plugin.json`, which declares `./skills/` as the shared skill source and intentionally disables repository hooks for Codex.

## Development acceptance test

1. Install this repository through the current Codex local plugin or plugin-development mechanism.
2. Confirm every directory under `skills/` is discovered.
3. Open a clean session and verify that a relevant Investment OS request selects `using-investment-os` and the required domain skills.
4. Confirm the selected skill resolves the current repository HEAD before using policy.
5. Ask for a live account review without broker access. The result must return the repository-defined fail-closed status and no transaction candidate.
6. Run the synthetic behavior scenarios in `evals/` before release.

The repository is not yet listed in the official Codex plugin marketplace, so this document does not claim a marketplace install command. Add the exact user-facing command only after publication and a clean-machine verification.

## Bootstrap note

Codex relies on native skill discovery rather than the Claude session hook. Release acceptance must prove automatic selection in a clean session; file presence alone is not sufficient.
