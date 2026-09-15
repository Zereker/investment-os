export const BROKER_RUNTIME_SCHEMA_VERSION = "1.0";
export const CAPABILITY_NAMES = [
  "account_summary", "balances", "positions", "open_orders",
  "cash_transactions", "market_inputs", "alert_inventory", "standing_automations"
] as const;
export const CAPABILITY_STATES = [
  "available", "unavailable", "stale", "conflicting", "not_requested", "not_applicable"
] as const;
