# ChatGPT MCP deployment

ChatGPT cannot install this repository directly from its GitHub URL. Codex and
Claude Code can load repository marketplaces locally; ChatGPT connects custom
plugins through a remote MCP endpoint or installs a reviewed directory release.

This directory adds the remote MCP path without creating a second copy of
Investment OS policy.

## What the server exposes

- `load_investment_os` reads the installed canonical `SKILL.md` and only the
  numbered references required for the selected task.
- `list_investment_os_tasks` returns the supported task routing names.
- `validate_broker_runtime` applies the existing broker-neutral freshness,
  capability, and reconciliation gates. Reconciliation uses the canonical 0.5%
  relative tolerance and returns its component totals and differences.
- `assemble_broker_runtime` converts ephemeral connector results into the
  canonical runtime without guessing unavailable data. Each capability carries
  its own status, source, observation time, and optional error. The adapter
  accepts IBKR's `balances.balances[]` and `positions.positions[]` envelopes;
  balance selection prefers the `BASE` row, then the snapshot currency basis.
- No tool writes to a broker.
- No tool stores account data.

The MCP server does not fetch IBKR data itself. In ChatGPT, enable the existing
Interactive Brokers plugin alongside Investment OS. Account-dependent work must
use fresh IBKR output, pass each connector result to `assemble_broker_runtime`,
and then pass its `runtime` to `validate_broker_runtime`; otherwise that path
remains `DATA INCOMPLETE`. A connector error stays unavailable—the adapter does
not repair, replace, or estimate broker data.

## Run locally

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-mcp.txt
python -m mcp_server.server
```

The Streamable HTTP endpoint is available at:

```text
http://localhost:8000/mcp
```

Test it with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector@latest
```

## Deploy on Cloudflare Workers Free

The repository includes a native, stateless TypeScript MCP Worker. It bundles
the canonical Skill and policy references at build time and does not require
Containers or a paid Workers plan.

```bash
npm install
npm run check:cloudflare
npm run test:cloudflare
npx wrangler login
npm run deploy:cloudflare
```

Wrangler prints a URL similar to:

```text
https://investment-os-mcp.YOUR_SUBDOMAIN.workers.dev
```

Connect ChatGPT to the same URL with `/mcp` appended. The initial deployment
is intentionally unauthenticated and exposes only read-only policy loading and
runtime validation. Do not add broker credentials or account storage to the
Worker.

## Run with Docker

```bash
docker build -t investment-os-mcp .
docker run --rm -p 8000:8000 investment-os-mcp
```

## Connect from ChatGPT

ChatGPT requires a reachable HTTPS endpoint. For temporary development, expose
port 8000 with an HTTPS tunnel. For continued use, deploy the Docker image to a
service that preserves the `PORT` environment variable and supports streaming
HTTP responses.

1. Open ChatGPT Settings, then Security and login, and enable Developer mode.
2. Open the ChatGPT Plugins page and create a plugin connection.
3. Enter `https://YOUR_HOST/mcp`.
4. Start a new chat and enable both Investment OS and Interactive Brokers.
5. Ask `Daily` or another supported Investment OS task.

The server is stateless. Do not add request-body logging, account snapshots,
credentials, authorization records, or execution receipts to the repository or
hosting logs.

## Verification

Repository checks:

```bash
bash tests/run-all.sh
```

Production remote MCP verification (no ChatGPT session required):

```bash
npm run verify:mcp
```

The verifier checks protocol initialization, the exact tool and task catalogs,
bundled policy equality, IBKR-shaped envelope normalization, NAV reconciliation,
localized fail-closed behavior, and the no-persistence declaration. It sends
synthetic data only. Override the endpoint with `INVESTMENT_OS_MCP_URL` when
testing another deployment. A scheduled GitHub Actions workflow runs the same
smoke test daily and can also be started manually.

MCP integration check after installing dependencies:

```bash
python -c "from mcp_server.server import mcp; print(mcp.name)"
```

A public ChatGPT Plugins Directory release is a separate review and publication
step. A GitHub tag or deployment does not make the plugin publicly listed.
