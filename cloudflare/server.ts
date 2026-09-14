import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import { assembleBrokerRuntime } from "./adapter";
import { isInvestmentTask, loadTaskContext, taskReferences } from "./policy";
import { validateBrokerRuntime } from "./runtime";

function jsonResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
    structuredContent: value as Record<string, unknown>
  };
}

function createServer() {
  const server = new McpServer(
    { name: "Investment OS", version: "0.17.4" },
    {
      instructions: [
        "Investment OS is rules-first and read-only.",
        "Call load_investment_os before answering an Investment OS task.",
        "Use assemble_broker_runtime to normalize connector results before validation.",
        "Never infer live account state or treat pasted figures as authoritative.",
        "Account-dependent paths require fresh broker output and PASS from validate_broker_runtime.",
        "Missing, stale, conflicting, or unverified data leaves only the affected path DATA INCOMPLETE.",
        "This server never submits orders and never persists portfolio data."
      ].join(" ")
    }
  );

  server.registerTool(
    "list_investment_os_tasks",
    {
      description: "List task names accepted by load_investment_os.",
      inputSchema: {}
    },
    async () => jsonResult({ tasks: Object.keys(taskReferences) })
  );

  server.registerTool(
    "load_investment_os",
    {
      description:
        "Load the canonical Skill and task-required policy references. Call this before every Investment OS answer.",
      inputSchema: {
        task: z.string().describe(
          "One of daily, monthly_funding, periodic_review, transaction_judgment, research, broker_execution, or system_audit"
        )
      }
    },
    async ({ task }) => {
      const normalized = task.trim().toLowerCase();
      if (!isInvestmentTask(normalized)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Unsupported task ${JSON.stringify(task)}. Use list_investment_os_tasks first.`
            }
          ],
          isError: true
        };
      }
      return jsonResult(loadTaskContext(normalized));
    }
  );

  server.registerTool(
    "assemble_broker_runtime",
    {
      description:
        "Deterministically assemble ephemeral IBKR connector results, including balances and positions envelopes, into the canonical Investment OS runtime. Missing, stale, conflicting, and failed connector capabilities remain explicit and are never guessed.",
      inputSchema: {
        identity: z.record(z.string(), z.unknown()),
        snapshot: z.record(z.string(), z.unknown()),
        capabilities: z.record(
          z.string(),
          z.object({
            status: z.enum(["available", "unavailable", "stale", "conflicting"]),
            data: z.unknown().optional(),
            source: z.string().optional(),
            observed_at: z.string().optional(),
            error: z.string().optional()
          })
        )
      }
    },
    async ({ identity, snapshot, capabilities }) =>
      jsonResult(assembleBrokerRuntime({ identity, snapshot, capabilities }))
  );

  server.registerTool(
    "validate_broker_runtime",
    {
      description:
        "Validate ephemeral authoritative broker facts before an account-dependent judgment. This tool never stores the payload or writes to a broker.",
      inputSchema: {
        runtime: z.record(z.string(), z.unknown()),
        required_capabilities: z.array(z.string()).default([]),
        max_age_seconds: z.number().int().min(1).max(3600).default(300)
      }
    },
    async ({ runtime, required_capabilities, max_age_seconds }) =>
      jsonResult(
        validateBrokerRuntime(
          runtime,
          required_capabilities,
          max_age_seconds
        )
      )
  );

  return server;
}

export default {
  fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/") {
      return Promise.resolve(
        new Response("Investment OS MCP server. Connect an MCP client at /mcp.")
      );
    }
    return createMcpHandler(createServer)(request, env, ctx);
  }
} satisfies ExportedHandler;
