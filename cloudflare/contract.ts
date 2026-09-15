export const BROKER_RUNTIME_SCHEMA_VERSION = "1.0";
export const SERVER_NAME = "Investment OS";
export const SERVER_VERSION = "0.20.1";
export const CAPABILITY_NAMES = [
  "account_summary", "balances", "positions", "open_orders",
  "cash_transactions", "market_inputs", "alert_inventory", "standing_automations"
] as const;
export const CAPABILITY_STATES = [
  "available", "unavailable", "stale", "conflicting", "not_requested", "not_applicable"
] as const;

export const BROKER_RUNTIME_CONTRACT = {
  schema_version: BROKER_RUNTIME_SCHEMA_VERSION,
  snapshot: {
    type: "object",
    required: ["as_of", "source", "timezone", "currency_basis"],
    additional_properties: false,
    as_of_format: "date-time"
  },
  capabilities: {
    type: "object",
    names: CAPABILITY_NAMES,
    states: CAPABILITY_STATES,
    additional_properties: false,
    data_shapes: {
      account_summary: ["net_liquidation"],
      balances: ["total_cash|cash", "balances[].currency", "balances[].cash_balance", "balances[].settled_cash?", "balances[].exchange_rate?"],
      positions: ["Position[]|{positions:Position[]}", "Position.symbol?", "Position.market_value"],
      open_orders: ["unknown[]|{orders:unknown[]}"],
      cash_transactions: ["unknown[]|{transactions:unknown[]}"],
      market_inputs: ["Record<string,unknown>"],
      alert_inventory: ["unknown[]|{alerts:unknown[]}"],
      standing_automations: ["unknown[]|{automations:unknown[]}"]
    }
  },
  required_capabilities: { type: "array", items: CAPABILITY_NAMES },
  alias_guidance: {
    account_balances: "balances",
    account_positions: "positions",
    account_orders: "open_orders"
  }
} as const;
