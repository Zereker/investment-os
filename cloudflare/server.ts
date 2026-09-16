import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

import { assembleBrokerRuntime } from "./adapter";
import { isInvestmentTask, loadTaskContext, taskReferences } from "./policy";
import { validateBrokerRuntime } from "./runtime";
import { calculateMonthlyDeployment } from "./monthly";
import { validateBrokerExecution } from "./execution";
import { CAPABILITY_NAMES, CAPABILITY_STATES, SERVER_NAME, SERVER_VERSION } from "./contract";

function jsonResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
    structuredContent: value as Record<string, unknown>
  };
}

const numeric = z.union([z.number(), z.string().regex(/^-?(?:\d+\.?\d*|\.\d+)$/)]);
const accountSummaryData = z.object({ net_liquidation: numeric }).passthrough();
const balanceRow = z.object({
  currency: z.string(), cash_balance: numeric,
  settled_cash: numeric.optional(), exchange_rate: numeric.optional()
}).passthrough();
const balancesData = z.union([
  z.object({ total_cash: numeric, settled_cash: numeric.optional() }).passthrough(),
  z.object({ cash: numeric, settled_cash: numeric.optional() }).passthrough(),
  z.object({ balances: z.array(balanceRow) }).passthrough()
]);
const positionRow = z.object({
  market_value: numeric,
  symbol: z.string().optional()
}).passthrough();
const positionsData = z.union([
  z.array(positionRow),
  z.object({ positions: z.array(positionRow) }).passthrough()
]);
const rowsOrEnvelope = (key: string) => z.union([
  z.array(z.unknown()),
  z.object({ [key]: z.array(z.unknown()) }).passthrough()
]);
const capabilityInput = <T extends z.ZodType>(dataSchema: T) => z.object({
  status: z.enum(CAPABILITY_STATES), data: dataSchema.optional(),
  source: z.string().optional(), observed_at: z.string().optional(), error: z.string().optional()
}).strict();
const capabilitiesInput = z.object({
  account_summary: capabilityInput(accountSummaryData).optional(),
  balances: capabilityInput(balancesData).optional(),
  positions: capabilityInput(positionsData).optional(),
  open_orders: capabilityInput(rowsOrEnvelope("orders")).optional(),
  cash_transactions: capabilityInput(rowsOrEnvelope("transactions")).optional(),
  market_inputs: capabilityInput(z.record(z.string(), z.unknown())).optional(),
  alert_inventory: capabilityInput(rowsOrEnvelope("alerts")).optional(),
  standing_automations: capabilityInput(rowsOrEnvelope("automations")).optional()
}).strict();

const taskName = z.enum([
  "daily", "monthly_funding", "periodic_review", "transaction_judgment",
  "research", "broker_execution", "system_audit"
]);
const serverMetadata = z.object({ name: z.string(), version: z.string() }).strict();
const reconciliationOutput = z.object({
  status: z.enum(["PASS", "DATA INCOMPLETE"]),
  issues: z.array(z.string()),
  nav: z.number().nullable(),
  cash: z.number().nullable(),
  positions_market_value: z.number().nullable(),
  component_total: z.number().nullable(),
  absolute_difference: z.number().nullable(),
  relative_difference: z.number().nullable(),
  tolerance: z.number(),
  diagnostic: z.string().nullable()
}).strict();
const capabilityStateOutput = z.enum(CAPABILITY_STATES);
const capabilityStatesOutput = z.object({
  account_summary: capabilityStateOutput,
  balances: capabilityStateOutput,
  positions: capabilityStateOutput,
  open_orders: capabilityStateOutput,
  cash_transactions: capabilityStateOutput,
  market_inputs: capabilityStateOutput,
  alert_inventory: capabilityStateOutput,
  standing_automations: capabilityStateOutput
}).strict();
const observationOutput = z.object({
  source: z.string().optional(),
  observed_at: z.string().optional()
}).strict();
const runtimeOutput = z.object({
  schema_version: z.literal("1.0"),
  identity: z.record(z.string(), z.unknown()),
  snapshot: z.object({
    as_of: z.iso.datetime({ offset: true }),
    source: z.string(),
    timezone: z.string(),
    currency_basis: z.string()
  }).strict(),
  capabilities: capabilityStatesOutput,
  observations: z.record(z.string(), observationOutput),
  account_summary: accountSummaryData.nullable(),
  balances: balancesData.nullable(),
  positions: z.array(positionRow).nullable(),
  open_orders: rowsOrEnvelope("orders").nullable(),
  cash_transactions: rowsOrEnvelope("transactions").nullable(),
  market_inputs: z.record(z.string(), z.unknown()).nullable(),
  alert_inventory: rowsOrEnvelope("alerts").nullable(),
  standing_automations: rowsOrEnvelope("automations").nullable(),
  reconciliation: reconciliationOutput
}).strict();
const allocationOutput = z.object({
  spym: z.number(), qqqm: z.number(), soxx: z.number()
}).strict();

function createServer() {
  const server = new McpServer(
    { name: SERVER_NAME, version: SERVER_VERSION },
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
      inputSchema: {},
      outputSchema: {
        server: serverMetadata,
        tasks: z.array(taskName)
      }
    },
    async () => jsonResult({
      server: { name: SERVER_NAME, version: SERVER_VERSION },
      tasks: Object.keys(taskReferences)
    })
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
      },
      outputSchema: {
        task: taskName,
        server: serverMetadata,
        broker_runtime_contract: z.record(z.string(), z.unknown()),
        skill: z.string(),
        references: z.record(z.string(), z.string()),
        source: z.string(),
        runtime_data_persisted: z.literal(false)
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
        schema_version: z.literal("1.0").default("1.0").describe("Broker runtime contract version accepted by both assemble and validate"),
        identity: z.record(z.string(), z.unknown()).describe("Broker-neutral account identity metadata. This object is intentionally extensible and is not an authorization claim."),
        snapshot: z.object({
          as_of: z.iso.datetime({ offset: true }).describe("ISO-8601 timezone-aware snapshot timestamp"),
          source: z.string().min(1), timezone: z.string().min(1),
          currency_basis: z.string().min(1).describe("Real account base currency code, for example USD")
        }).strict(),
        capabilities: capabilitiesInput,
        required_capabilities: z.array(z.enum(CAPABILITY_NAMES)).default([])
      },
      outputSchema: {
        adapter_status: z.enum(["PASS", "PASS_WITH_OPTIONAL_GAPS", "DATA INCOMPLETE"]),
        required_status: z.enum(["PASS", "DATA INCOMPLETE"]),
        optional_status: z.enum(["PASS", "PARTIAL"]),
        adapter_issues: z.array(z.string()),
        runtime: runtimeOutput,
        schema_version: z.literal("1.0"),
        runtime_data_persisted: z.literal(false)
      }
    },
    async ({ schema_version, identity, snapshot, capabilities, required_capabilities }) =>
      jsonResult(assembleBrokerRuntime({ schema_version, identity, snapshot, capabilities, required_capabilities }))
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
      },
      outputSchema: {
        schema_version: z.literal("1.0"),
        runtime_status: z.enum(["PASS", "DATA INCOMPLETE"]),
        blocking_issues: z.array(z.string()),
        observation_skew_seconds: z.number().nullable(),
        reconciliation: reconciliationOutput
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
      },
      outputSchema: {
        status: z.enum(["PASS", "DATA INCOMPLETE"]),
        blocking_issues: z.array(z.string()),
        weights: z.object({ spym: z.number(), qqqm: z.number(), soxx: z.number(), cash: z.number() }).strict(),
        gaps: allocationOutput,
        routine_dca: z.object({ amount: z.number(), allocation: allocationOutput }).strict(),
        strategic_baseline: z.object({ surplus: z.number(), amount: z.number(), allocation: allocationOutput }).strict(),
        drawdown_deployment: z.object({
          evaluated: z.boolean(),
          allocation: allocationOutput,
          consumed_tiers: z.object({
            spym: z.array(z.string()), qqqm: z.array(z.string()), soxx: z.array(z.string())
          }).strict()
        }).strict(),
        final_cash: z.number(),
        execution_authorized: z.literal(false),
        runtime_data_persisted: z.literal(false)
      }
    },
    async (input) => jsonResult(calculateMonthlyDeployment(input))
  );

  server.registerTool(
    "validate_broker_execution",
    {
      description: "Validate one broker operation lifecycle, authorization binding, single-submit semantics, and authoritative read-back. This tool never submits an order.",
      inputSchema: { record: z.record(z.string(), z.unknown()) },
      outputSchema: {
        status: z.enum(["COMPLETED", "NOT EXECUTED", "EXECUTION UNKNOWN", "VERIFICATION FAILED"]),
        issues: z.array(z.string()),
        passed: z.boolean()
      }
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
