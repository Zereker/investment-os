# Install in Codex

Investment OS is a skills-only Codex plugin. Install it once from the repository marketplace; Codex then loads the installed cache copy and discovers `./skills/` through `.codex-plugin/plugin.json`. The user does not clone the repository or run Codex from the Investment OS source directory.

## Install

Add the repository marketplace:

```bash
codex plugin marketplace add Zereker/investment-os --ref master
```

Then install the plugin:

```bash
codex plugin add investment-os@investment-os
```

Start a new Codex session after installation. Relevant requests may select `using-investment-os` implicitly; use `$using-investment-os` when explicit selection is needed.

The installed plugin is an immutable session input. Skills resolve policy files and deterministic scripts from their installed plugin root, never from the current working directory and never by cloning or fetching a newer Investment OS checkout at runtime.

## Development acceptance test

1. Install this repository through the marketplace commands above, using a clean Codex home for release acceptance.
2. Confirm every directory under `skills/` is discovered.
3. Open a clean session and verify that a relevant Investment OS request selects `using-investment-os` and the required domain skills.
4. Confirm the selected skill reads the policy files distributed with the installation and reports the distribution version, without attempting to fetch a newer policy version at runtime.
5. Ask for a live account review without broker access. The result must return the repository-defined fail-closed status and no transaction candidate.
6. Run the synthetic behavior scenarios in `evals/` before release.

The repository marketplace is a direct distribution channel, not an OpenAI public-directory listing. Public-directory availability requires a separate submission and review.

## Bootstrap note

Codex relies on native skill discovery rather than the Claude session hook. The Codex package intentionally contains neither a `hooks` manifest field nor the default `hooks/hooks.json` path. Release acceptance must prove automatic selection in a clean session; file presence alone is not sufficient.
