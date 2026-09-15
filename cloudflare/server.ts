import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import { assembleBrokerRuntime } from "./adapter";
import { isInvestmentTask, loadTaskContext, taskReferences } from "./policy";
import { validateBrokerRuntime } from "./runtime";
import { calculateMonthlyDeployment } from "./monthly";
import { validateBrokerExecution } from "./execution";
import { CAPABILITY_NAMES, CAPABILITY_STATES } from "./contract";

function jsonResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
    structuredContent: value as Record<string, unknown>
  };
}

const capabilityInput = z.object({
  status: z.enum(CAPABILITY_STATES),
  data: z.unknown().optional(), source: z.string().optional(),
  observed_at: z.string().optional(), error: z.string().optional()
}).strict();
const capabilitiesInput = z.object(Object.fromEntries(
  CAPABILITY_NAMES.map((name) => [name, capabilityInput.optional()])
) as Record<(typeof CAPABILITY_NAMES)[number], z.ZodOptional<typeof capabilityInput>>).strict();

function createServer() {
  const server = new McpServer(
    { name: "Investment OS", version: "0.19.0" },
    {
      instructions: [
        "Investment OS is rules-first and read-only.",
        "Call load_investment_os before answering an Investment OS task.",
        "Use assemble_broker_runtime to normalize connector results before validation.",
        "Never infer live account state or treat pasted figures as authoritative.",
        "Account-dependent paths require fresh broker output and PASS from validate_broker_runtime.",
        "Missing, stale, conflicting, or unverified data leaves only the affected path DATA INCOMPLETE.",
        "This server never submits orders and never persists portfolio data."
        ,"Before sending private broker data from another connector, obtain explicit current-session consent for ephemeral processing."
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
        "Deterministically assemble ephemeral IBKR connector results into canonical runtime schema 1.0. Use exactly account_summary, balances, positions, open_orders, cash_transactions, market_inputs, alert_inventory, and standing_automations; aliases such as account_balances, account_positions, and account_orders are invalid. Omitted optional capabilities become not_requested. Pass required_capabilities to scope status. Obtain explicit consent before passing private data from another connector; data is never persisted.",
      inputSchema: {
        identity: z.record(z.string(), z.unknown()),
        snapshot: z.object({
          as_of: z.iso.datetime({ offset: true }).describe("ISO-8601 timezone-aware snapshot timestamp"),
          source: z.string().min(1), timezone: z.string().min(1),
          currency_basis: z.string().min(1).describe("Real account base currency code, for example USD")
        }).strict(),
        capabilities: capabilitiesInput,
        required_capabilities: z.array(z.enum(CAPABILITY_NAMES)).default([])
      }
    },
    async ({ identity, snapshot, capabilities, required_capabilities }) =>
      jsonResult(assembleBrokerRuntime({ identity, snapshot, capabilities, required_capabilities }))
  );

  server.registerTool(
    "validate_broker_runtime",
    {
      description:
        "Validate ephemeral authoritative broker facts before an account-dependent judgment. This tool never stores the payload or writes to a broker.",
      inputSchema: {
        runtime: z.record(z.string(), z.unknown()),
        required_capabilities: z.array(z.enum(CAPABILITY_NAMES)).default([]),
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

  server.registerTool(
    "calculate_monthly_deployment",
    {
      description: "Calculate the policy-defined monthly funding candidates from validated ephemeral inputs. This never authorizes or submits an order.",
      inputSchema: {
        nav: z.number(), cash: z.number(),
        positions: z.object({ spym: z.number(), qqqm: z.number(), soxx: z.number() }),
        legacy: z.number().default(0), contribution: z.number().nullable(),
        open_orders_status: z.enum(["clear", "conflicting", "unknown"]),
        drawdowns: z.object({ spym: z.number().optional(), qqqm: z.number().optional() }).optional(),
        tiers_executed: z.object({ spym: z.array(z.string()).optional(), qqqm: z.array(z.string()).optional() }).optional(),
        drawdown_as_of: z.string().optional(), today: z.string().optional()
      }
    },
    async (input) => jsonResult(calculateMonthlyDeployment(input))
  );

  server.registerTool(
    "validate_broker_execution",
    {
      description: "Validate one broker operation lifecycle, authorization binding, single-submit semantics, and authoritative read-back. This tool never submits an order.",
      inputSchema: { record: z.record(z.string(), z.unknown()) }
    },
    async ({ record }) => jsonResult(validateBrokerExecution(record))
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
