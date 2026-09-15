import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const ENDPOINT =
  process.env.INVESTMENT_OS_MCP_URL ??
  "https://investment-os-mcp.444002.xyz/mcp";
const EXPECTED_TOOLS = [
  "assemble_broker_runtime",
  "calculate_monthly_deployment",
  "list_investment_os_tasks",
  "load_investment_os",
  "validate_broker_execution",
  "validate_broker_runtime"
];
const EXPECTED_TASKS = [
  "daily",
  "monthly_funding",
  "periodic_review",
  "transaction_judgment",
  "research",
  "broker_execution",
  "system_audit"
];

type JsonObject = Record<string, unknown>;

function object(value: unknown, label: string): JsonObject {
  assert.ok(value !== null && typeof value === "object" && !Array.isArray(value), `${label} must be an object`);
  return value as JsonObject;
}

async function rpc(method: string, params: JsonObject): Promise<JsonObject> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch(ENDPOINT, {
        method: "POST",
        headers: {
          Accept: "application/json, text/event-stream",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ jsonrpc: "2.0", id: attempt, method, params }),
        signal: AbortSignal.timeout(30_000)
      });
      const body = await response.text();
      assert.ok(response.ok, `${method} returned HTTP ${response.status}: ${body}`);
      const dataLine = body
        .split(/\r?\n/)
        .find((line) => line.startsWith("data: "));
      const payload = JSON.parse(dataLine ? dataLine.slice(6) : body) as JsonObject;
      assert.ok(!payload.error, `${method} returned ${JSON.stringify(payload.error)}`);
      return object(payload.result, `${method} result`);
    } catch (error) {
      lastError = error;
      if (attempt === 3) break;
    }
  }
  throw lastError;
}

function structuredContent(result: JsonObject): JsonObject {
  return object(result.structuredContent, "structuredContent");
}

function available(data: unknown, observedAt: string, source: string) {
  return { status: "available", data, observed_at: observedAt, source };
}

async function main() {
  const packageJson = JSON.parse(
    await readFile(resolve(ROOT, "package.json"), "utf8")
  ) as JsonObject;

  const initialized = await rpc("initialize", {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: { name: "investment-os-production-verifier", version: "1.0.0" }
  });
  const serverInfo = object(initialized.serverInfo, "serverInfo");
  assert.equal(serverInfo.name, "Investment OS");
  assert.equal(serverInfo.version, packageJson.version);

  const listed = await rpc("tools/list", {});
  const tools = listed.tools as Array<JsonObject>;
  assert.ok(Array.isArray(tools), "tools/list must return an array");
  assert.deepEqual(
    tools.map((tool) => tool.name).sort(),
    EXPECTED_TOOLS
  );

  const taskResult = structuredContent(
    await rpc("tools/call", {
      name: "list_investment_os_tasks",
      arguments: {}
    })
  );
  assert.deepEqual(taskResult.tasks, EXPECTED_TASKS);

  const policy = structuredContent(
    await rpc("tools/call", {
      name: "load_investment_os",
      arguments: { task: "system_audit" }
    })
  );
  assert.equal(policy.runtime_data_persisted, false);
  assert.equal(
    policy.skill,
    await readFile(resolve(ROOT, "skills/investment-os/SKILL.md"), "utf8")
  );
  const references = object(policy.references, "policy references");
  assert.deepEqual(Object.keys(references).sort(), [
    "00-constitution.md",
    "06-data-contract.md"
  ]);
  for (const name of Object.keys(references)) {
    assert.equal(
      references[name],
      await readFile(
        resolve(ROOT, "skills/investment-os/references", name),
        "utf8"
      )
    );
  }

  const observedAt = new Date().toISOString();
  const capabilities = {
    account_summary: available(
      { net_liquidation: 100_000 },
      observedAt,
      "synthetic IBKR account summary"
    ),
    balances: available(
      {
        balances: [
          { currency: "BASE", cash_balance: 15_000, settled_cash: 14_900 },
          { currency: "USD", cash_balance: 14_000, settled_cash: 13_900 }
        ]
      },
      observedAt,
      "synthetic IBKR balances"
    ),
    positions: available(
      { positions: [{ symbol: "SYNTHETIC", market_value: 84_900 }] },
      observedAt,
      "synthetic IBKR positions"
    ),
    open_orders: available([], observedAt, "synthetic IBKR orders"),
    cash_transactions: available([], observedAt, "synthetic IBKR activity"),
    market_inputs: available({}, observedAt, "synthetic IBKR market data"),
    alert_inventory: available([], observedAt, "synthetic IBKR alerts"),
    standing_automations: available([], observedAt, "synthetic IBKR automations")
  };
  const baseArguments = {
    identity: { account_id: "SYNTHETIC", account_type: "paper" },
    snapshot: {
      as_of: observedAt,
      source: "synthetic IBKR connector",
      timezone: "UTC",
      currency_basis: "USD"
    },
    capabilities
  };
  const assembled = structuredContent(
    await rpc("tools/call", {
      name: "assemble_broker_runtime",
      arguments: baseArguments
    })
  );
  assert.equal(assembled.adapter_status, "PASS");
  assert.equal(assembled.runtime_data_persisted, false);
  const runtime = object(assembled.runtime, "assembled runtime");
  assert.deepEqual(runtime.balances, {
    total_cash: 15_000,
    settled_cash: 14_900,
    currency: "BASE"
  });
  assert.deepEqual(runtime.positions, [
    { symbol: "SYNTHETIC", market_value: 84_900 }
  ]);

  const validated = structuredContent(
    await rpc("tools/call", {
      name: "validate_broker_runtime",
      arguments: {
        runtime,
        required_capabilities: [
          "account_summary",
          "balances",
          "positions",
          "open_orders"
        ],
        max_age_seconds: 300
      }
    })
  );
  assert.equal(validated.runtime_status, "PASS");
  assert.deepEqual(validated.blocking_issues, []);
  const reconciliation = object(validated.reconciliation, "reconciliation");
  assert.equal(reconciliation.absolute_difference, 100);
  assert.equal(reconciliation.relative_difference, 0.001);
  assert.equal(reconciliation.tolerance, 0.005);

  const failedOrdersArguments = structuredClone(baseArguments);
  failedOrdersArguments.capabilities.open_orders = {
    status: "unavailable",
    error: "synthetic upstream error"
  } as never;
  const failedOrders = structuredContent(
    await rpc("tools/call", {
      name: "assemble_broker_runtime",
      arguments: failedOrdersArguments
    })
  );
  assert.equal(failedOrders.adapter_status, "WARN");
  const failedOrdersRuntime = object(failedOrders.runtime, "failed-orders runtime");
  assert.equal(failedOrdersRuntime.open_orders, null);
  const failedOrdersValidation = structuredContent(
    await rpc("tools/call", {
      name: "validate_broker_runtime",
      arguments: {
        runtime: failedOrdersRuntime,
        required_capabilities: ["open_orders"],
        max_age_seconds: 300
      }
    })
  );
  assert.equal(failedOrdersValidation.runtime_status, "DATA INCOMPLETE");
  assert.ok(
    (failedOrdersValidation.blocking_issues as string[]).some((issue) =>
      issue.includes("open_orders is unavailable")
    )
  );

  const failedBalancesArguments = structuredClone(baseArguments);
  failedBalancesArguments.capabilities.balances = {
    status: "unavailable",
    error: "synthetic upstream error"
  } as never;
  const failedBalances = structuredContent(
    await rpc("tools/call", {
      name: "assemble_broker_runtime",
      arguments: failedBalancesArguments
    })
  );
  const failedBalancesRuntime = object(
    failedBalances.runtime,
    "failed-balances runtime"
  );
  assert.equal(failedBalancesRuntime.balances, null);
  const failedReconciliation = object(
    failedBalancesRuntime.reconciliation,
    "failed reconciliation"
  );
  assert.equal(failedReconciliation.status, "DATA INCOMPLETE");
  assert.equal(failedReconciliation.cash, null);

  console.log(
    `Remote MCP verification passed: ${serverInfo.name} ${serverInfo.version} at ${ENDPOINT}`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
