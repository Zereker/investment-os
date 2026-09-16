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

function toolErrorText(result: JsonObject): string {
  assert.equal(result.isError, true, "tool call must fail at input validation");
  const content = result.content as Array<JsonObject>;
  assert.ok(Array.isArray(content), "error result content must be an array");
  return content.map((item) => item.text).filter((text): text is string => typeof text === "string").join("\n");
}

async function expectToolError(arguments_: JsonObject, fragments: string[]) {
  const result = await rpc("tools/call", { name: "assemble_broker_runtime", arguments: arguments_ });
  const text = toolErrorText(result);
  for (const fragment of fragments) assert.match(text, new RegExp(fragment), text);
  return text;
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
  for (const tool of tools) {
    const outputSchema = object(tool.outputSchema, `${String(tool.name)} outputSchema`);
    assert.equal(outputSchema.type, "object", `${String(tool.name)} must publish an object outputSchema`);
    assert.equal(outputSchema.additionalProperties, false, `${String(tool.name)} outputSchema must reject undeclared top-level fields`);
  }
  const assembleTool = tools.find((tool) => tool.name === "assemble_broker_runtime");
  assert.ok(assembleTool, "assemble_broker_runtime must be published");
  const assembleSchema = object(assembleTool.inputSchema, "assemble inputSchema");
  const assembleProperties = object(assembleSchema.properties, "assemble properties");
  const schemaVersion = object(assembleProperties.schema_version, "schema version input");
  assert.equal(schemaVersion.const, "1.0");
  const snapshotSchema = object(assembleProperties.snapshot, "snapshot schema");
  assert.deepEqual(snapshotSchema.required, ["as_of", "source", "timezone", "currency_basis"]);
  assert.equal(snapshotSchema.additionalProperties, false);
  const capabilitiesSchema = object(assembleProperties.capabilities, "capabilities schema");
  assert.equal(capabilitiesSchema.additionalProperties, false);
  const capabilityProperties = object(capabilitiesSchema.properties, "capability properties");
  assert.deepEqual(Object.keys(capabilityProperties), [
    "account_summary", "balances", "positions", "open_orders",
    "cash_transactions", "market_inputs", "alert_inventory", "standing_automations"
  ]);
  const accountSummarySchema = object(capabilityProperties.account_summary, "account_summary schema");
  const accountSummaryProperties = object(accountSummarySchema.properties, "account_summary properties");
  const accountSummaryDataSchema = object(accountSummaryProperties.data, "account_summary data schema");
  assert.ok(JSON.stringify(accountSummaryDataSchema).includes("net_liquidation"));
  const statusSchema = object(accountSummaryProperties.status, "capability status schema");
  assert.deepEqual(statusSchema.enum, [
    "available", "unavailable", "stale", "conflicting", "not_requested", "not_applicable"
  ]);
  const requiredCapabilitiesSchema = object(assembleProperties.required_capabilities, "required capabilities schema");
  const requiredCapabilityItems = object(requiredCapabilitiesSchema.items, "required capability items");
  assert.deepEqual(requiredCapabilityItems.enum, Object.keys(capabilityProperties));
  const balancesSchema = object(capabilityProperties.balances, "balances capability schema");
  assert.ok(JSON.stringify(balancesSchema).includes("cash_balance"));
  const positionsSchema = object(capabilityProperties.positions, "positions capability schema");
  assert.ok(JSON.stringify(positionsSchema).includes("market_value"));
  const assembleOutputSchema = object(assembleTool.outputSchema, "assemble outputSchema");
  const assembleOutputProperties = object(assembleOutputSchema.properties, "assemble output properties");
  assert.deepEqual(Object.keys(assembleOutputProperties), [
    "adapter_status", "required_status", "optional_status", "adapter_issues",
    "runtime", "schema_version", "runtime_data_persisted"
  ]);
  assert.deepEqual(assembleOutputSchema.required, Object.keys(assembleOutputProperties));
  const runtimeOutputSchema = object(assembleOutputProperties.runtime, "runtime output schema");
  assert.equal(runtimeOutputSchema.additionalProperties, false);
  const runtimeOutputProperties = object(runtimeOutputSchema.properties, "runtime output properties");
  assert.ok(runtimeOutputProperties.reconciliation, "runtime output must publish reconciliation");
  assert.deepEqual(
    object(runtimeOutputProperties.capabilities, "runtime capability states").required,
    Object.keys(capabilityProperties)
  );

  const taskResult = structuredContent(
    await rpc("tools/call", {
      name: "list_investment_os_tasks",
      arguments: {}
    })
  );
  assert.deepEqual(taskResult.tasks, EXPECTED_TASKS);
  assert.deepEqual(taskResult.server, { name: "Investment OS", version: packageJson.version });

  const policy = structuredContent(
    await rpc("tools/call", {
      name: "load_investment_os",
      arguments: { task: "system_audit" }
    })
  );
  assert.equal(policy.runtime_data_persisted, false);
  assert.deepEqual(policy.server, { name: "Investment OS", version: packageJson.version });
  const declaredContract = object(policy.broker_runtime_contract, "declared broker runtime contract");
  assert.equal(declaredContract.schema_version, schemaVersion.const);
  const declaredSnapshot = object(declaredContract.snapshot, "declared snapshot contract");
  assert.deepEqual(declaredSnapshot.required, snapshotSchema.required);
  assert.equal(declaredSnapshot.additional_properties, snapshotSchema.additionalProperties);
  const declaredCapabilities = object(declaredContract.capabilities, "declared capabilities contract");
  assert.deepEqual(declaredCapabilities.names, Object.keys(capabilityProperties));
  assert.deepEqual(declaredCapabilities.states, statusSchema.enum);
  const declaredShapes = object(declaredCapabilities.data_shapes, "declared data shapes");
  assert.ok(JSON.stringify(declaredShapes.account_summary).includes("net_liquidation"));
  assert.ok(JSON.stringify(declaredShapes.balances).includes("cash_balance"));
  assert.ok(JSON.stringify(declaredShapes.positions).includes("market_value"));
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
    schema_version: "1.0",
    identity: { account_id: "SYNTHETIC", account_type: "paper" },
    snapshot: {
      as_of: observedAt,
      source: "synthetic IBKR connector",
      timezone: "UTC",
      currency_basis: "USD"
    },
    capabilities,
    required_capabilities: ["account_summary", "balances", "positions", "open_orders"]
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
    currency_basis: "USD",
    base_currency: "USD",
    selected_balance_label: "BASE",
    selection_reason: "IBKR BASE aggregate selected for account currency basis",
    by_currency: [
      { currency: "BASE", cash_balance: 15_000, settled_cash: 14_900 },
      { currency: "USD", cash_balance: 14_000, settled_cash: 13_900 }
    ]
  });
  assert.equal(runtime.schema_version, "1.0");
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
  assert.match(String(reconciliation.diagnostic), /diagnostic only/);

  const minimumArguments = structuredClone(baseArguments);
  minimumArguments.capabilities = Object.fromEntries(
    Object.entries(minimumArguments.capabilities).filter(([name]) =>
      minimumArguments.required_capabilities.includes(name)
    )
  ) as never;
  const minimum = structuredContent(await rpc("tools/call", {
    name: "assemble_broker_runtime", arguments: minimumArguments
  }));
  assert.equal(minimum.adapter_status, "PASS");
  assert.equal(minimum.required_status, "PASS");
  assert.equal(object(object(minimum.runtime, "minimum runtime").capabilities, "minimum capabilities").market_inputs, "not_requested");

  const notApplicableArguments = structuredClone(minimumArguments);
  notApplicableArguments.capabilities.market_inputs = { status: "not_applicable" } as never;
  const notApplicable = structuredContent(await rpc("tools/call", {
    name: "assemble_broker_runtime", arguments: notApplicableArguments
  }));
  assert.equal(object(object(notApplicable.runtime, "not-applicable runtime").capabilities, "not-applicable capabilities").market_inputs, "not_applicable");
  assert.equal(notApplicable.adapter_status, "PASS");

  const aliasError = await expectToolError({
    ...baseArguments,
    capabilities: {
      account_balances: capabilities.balances,
      account_positions: capabilities.positions,
      account_orders: capabilities.open_orders
    }
  }, ["account_balances", "account_positions", "account_orders"]);
  assert.match(aliasError, /Unrecognized key/i);

  await expectToolError({
    ...baseArguments,
    snapshot: { as_of: observedAt }
  }, ["snapshot.source", "snapshot.timezone", "snapshot.currency_basis"]);

  await expectToolError({ ...baseArguments, schema_version: "0.9" }, ["schema_version"]);

  const multiCurrencyArguments = structuredClone(minimumArguments);
  multiCurrencyArguments.capabilities.balances = available({ balances: [
    { currency: "BASE", cash_balance: 15_000, exchange_rate: 1 },
    { currency: "USD", cash_balance: 15_000, exchange_rate: 1 },
    { currency: "JPY", cash_balance: 100_000, exchange_rate: 0.0068 }
  ] }, observedAt, "synthetic IBKR balances") as never;
  const multiCurrency = structuredContent(await rpc("tools/call", {
    name: "assemble_broker_runtime", arguments: multiCurrencyArguments
  }));
  const normalizedBalances = object(object(multiCurrency.runtime, "multi-currency runtime").balances, "normalized balances");
  assert.equal(normalizedBalances.base_currency, "USD");
  assert.equal(normalizedBalances.selected_balance_label, "BASE");
  assert.match(String(normalizedBalances.selection_reason), /BASE aggregate selected/);
  assert.deepEqual(normalizedBalances.by_currency, (multiCurrencyArguments.capabilities.balances as JsonObject).data && object((multiCurrencyArguments.capabilities.balances as JsonObject).data, "balance input").balances);

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
  assert.equal(failedOrders.adapter_status, "DATA INCOMPLETE");
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

  const overToleranceArguments = structuredClone(baseArguments);
  overToleranceArguments.capabilities.positions = available(
    { positions: [{ symbol: "SYNTHETIC", market_value: 84_000 }] }, observedAt, "synthetic IBKR positions"
  ) as never;
  const overTolerance = structuredContent(await rpc("tools/call", {
    name: "assemble_broker_runtime", arguments: overToleranceArguments
  }));
  const overReconciliation = object(object(overTolerance.runtime, "over-tolerance runtime").reconciliation, "over-tolerance reconciliation");
  assert.equal(overReconciliation.status, "DATA INCOMPLETE");
  assert.match(String(overReconciliation.diagnostic), /exceeds tolerance/);
  assert.doesNotMatch(String(overReconciliation.diagnostic), /within tolerance/);
  const overValidated = structuredContent(await rpc("tools/call", {
    name: "validate_broker_runtime", arguments: { runtime: overTolerance.runtime, required_capabilities: baseArguments.required_capabilities, max_age_seconds: 3600 }
  }));
  assert.equal(overValidated.runtime_status, "DATA INCOMPLETE");

  const exactDifferenceArguments = structuredClone(baseArguments);
  exactDifferenceArguments.capabilities.positions = available(
    { positions: [{ symbol: "SYNTHETIC", market_value: 84_880.14 }] }, observedAt, "synthetic IBKR positions"
  ) as never;
  const exactDifference = structuredContent(await rpc("tools/call", {
    name: "assemble_broker_runtime", arguments: exactDifferenceArguments
  }));
  const exactReconciliation = object(object(exactDifference.runtime, "exact-difference runtime").reconciliation, "exact-difference reconciliation");
  assert.equal(exactReconciliation.status, "PASS");
  assert.ok(Math.abs(Number(exactReconciliation.absolute_difference) - 119.86) < 1e-8);
  assert.ok(Math.abs(Number(exactReconciliation.relative_difference) - 0.0011986) < 1e-12);
  assert.equal(exactReconciliation.tolerance, 0.005);
  assert.match(String(exactReconciliation.diagnostic), /diagnostic only/);

  for (const [label, offsetMs, expected] of [
    ["current", 0, "PASS"],
    ["stale", -7_301_000, "DATA INCOMPLETE"],
    ["future", 7_200_000, "DATA INCOMPLETE"]
  ] as const) {
    const timestamp = new Date(Date.now() + offsetMs).toISOString();
    const timeArguments = structuredClone(baseArguments);
    timeArguments.snapshot.as_of = timestamp;
    for (const capability of Object.values(timeArguments.capabilities)) capability.observed_at = timestamp;
    const timeAssembled = structuredContent(await rpc("tools/call", { name: "assemble_broker_runtime", arguments: timeArguments }));
    const timeValidated = structuredContent(await rpc("tools/call", {
      name: "validate_broker_runtime", arguments: { runtime: timeAssembled.runtime, required_capabilities: baseArguments.required_capabilities, max_age_seconds: 3600 }
    }));
    assert.equal(timeValidated.runtime_status, expected, `${label} timestamp status`);
    const issues = (timeValidated.blocking_issues as string[]).join("\n");
    if (label === "stale") assert.match(issues, /stale/);
    if (label === "future") assert.match(issues, /in the future/);
  }

  const monthly = structuredContent(await rpc("tools/call", {
    name: "calculate_monthly_deployment",
    arguments: { nav: 100000, cash: 34000, positions: { spym: 40000, qqqm: 20000, soxx: 6000 }, legacy: 0,
      contribution: 0, open_orders_status: "clear", drawdown_as_of: observedAt.slice(0, 10), today: observedAt.slice(0, 10),
      drawdowns: { spym: 0.04, qqqm: 0.21 }, tiers_executed: { spym: [], qqqm: [] } }
  }));
  assert.equal(monthly.status, "PASS");
  assert.equal(monthly.execution_authorized, false);

  const execution = structuredContent(await rpc("tools/call", {
    name: "validate_broker_execution",
    arguments: { record: { operation: { type: "place_order", account: "SYNTHETIC", instrument: "TEST", side: "BUY", quantity: 1,
      order_type: "LIMIT", limit_price: 10, time_in_force: "DAY" }, capability: "Broker.Trade.PlaceOrder",
      authorization: { scope: "single-operation-current-session", operation_digest: "7750551cc9b0a33805406be0e503d433cdb6067d01eb500600bbe9ad571c0137", owner_explicit: true, session_id: "synthetic-regression" },
      adapter: { supported_capabilities: ["Broker.Trade.PlaceOrder"] },
      stages: ["PREPARED", "CAPABILITY_CHECKED", "AUTHORIZED", "EXECUTED", "READ_BACK", "VERIFIED", "COMPLETED"], submit_count: 1,
      write_result: { accepted: true }, read_back: { status: "Submitted" }, verification: { performed: true, passed: true, evidence: "synthetic read-back matched" }, status: "COMPLETED" } }
  }));
  assert.equal(execution.passed, true);

  console.log(
    `Remote MCP verification passed: ${serverInfo.name} ${serverInfo.version} at ${ENDPOINT}`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
