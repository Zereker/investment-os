export const TARGETS = { cash: 0.15, spym: 0.50, qqqm: 0.30, soxx: 0.05 } as const;
export const LADDERS = { spym: 0.09, qqqm: 0.06 } as const;
const TICKERS = ["spym", "qqqm", "soxx"] as const;
const TIERS = [[0.10, "T1", 1], [0.15, "T2", 2], [0.20, "T3", 3], [0.25, "T4", 4]] as const;
type Ticker = typeof TICKERS[number];
type LadderTicker = keyof typeof LADDERS;

export type MonthlyInput = {
  nav: number; cash: number; positions: Record<Ticker, number>; legacy?: number;
  contribution: number | null; open_orders_status: "clear" | "conflicting" | "unknown";
  drawdowns?: Partial<Record<LadderTicker, number>>;
  tiers_executed?: Partial<Record<LadderTicker, string[]>>;
  drawdown_as_of?: string; today?: string;
};

function allocate(amount: number, gaps: Record<Ticker, number>) {
  const out = { spym: 0, qqqm: 0, soxx: 0 };
  let remaining = Math.max(amount, 0);
  for (const ticker of [...TICKERS].sort((a, b) => gaps[b] - gaps[a])) {
    out[ticker] = Math.min(remaining, Math.max(gaps[ticker], 0)); remaining -= out[ticker];
  }
  return out;
}

function fresh(asOf?: string, today?: string) {
  if (!asOf) return false;
  const a = Date.parse(`${asOf.slice(0, 10)}T00:00:00Z`), b = Date.parse(`${(today ?? new Date().toISOString()).slice(0, 10)}T00:00:00Z`);
  return Number.isFinite(a) && Number.isFinite(b) && b >= a && b - a <= 7 * 86400000;
}

export function calculateMonthlyDeployment(input: MonthlyInput) {
  const issues: string[] = [];
  const values = [input.nav, input.cash, ...TICKERS.map(t => input.positions[t]), input.legacy ?? 0];
  if (values.some(v => !Number.isFinite(v) || v < 0) || input.nav <= 0) issues.push("NAV and position inputs must be finite and nonnegative; NAV must be positive");
  if (input.contribution === null) issues.push("authoritative monthly contribution F is unavailable");
  else if (!Number.isFinite(input.contribution) || input.contribution < 0) issues.push("contribution must be finite and nonnegative");
  if (input.open_orders_status !== "clear") issues.push(`open orders status is ${input.open_orders_status}; must be clear`);
  const total = input.cash + TICKERS.reduce((s, t) => s + input.positions[t], 0) + (input.legacy ?? 0);
  if (Number.isFinite(input.nav) && Math.abs(input.nav - total) / input.nav > 0.005) issues.push("cash plus positions does not reconcile to NAV");
  for (const [ticker, dd] of Object.entries(input.drawdowns ?? {})) {
    if (!Number.isFinite(dd) || dd! < 0 || dd! >= 1) issues.push(`${ticker} drawdown must be a decimal in [0, 1)`);
  }
  const drawdownFresh = fresh(input.drawdown_as_of, input.today);
  const gaps = Object.fromEntries(TICKERS.map(t => [t, Math.max(TARGETS[t] * input.nav - input.positions[t], 0)])) as Record<Ticker, number>;
  const d = input.contribution === null ? 0 : Math.min(input.contribution, Object.values(gaps).reduce((a, b) => a + b, 0));
  const routine = allocate(d, gaps);
  const afterD = Object.fromEntries(TICKERS.map(t => [t, gaps[t] - routine[t]])) as Record<Ticker, number>;
  const surplus = Math.max(input.cash - d - TARGETS.cash * input.nav, 0);
  const baselineAmount = Math.min(surplus / 3, Object.values(afterD).reduce((a, b) => a + b, 0));
  const baseline = allocate(baselineAmount, afterD);
  const remainingGaps = Object.fromEntries(TICKERS.map(t => [t, afterD[t] - baseline[t]])) as Record<Ticker, number>;
  let remainingCash = input.cash - d - baselineAmount;
  const drawdown = { spym: 0, qqqm: 0, soxx: 0 };
  const consumed: Record<string, string[]> = { spym: [], qqqm: [], soxx: [] };
  if (drawdownFresh) for (const ticker of (Object.keys(LADDERS) as LadderTicker[]).sort((a,b) => (input.drawdowns?.[b] ?? 0) - (input.drawdowns?.[a] ?? 0))) {
    const dd = input.drawdowns?.[ticker];
    const known = input.tiers_executed?.[ticker];
    if (dd === undefined || known === undefined) continue;
    const newTiers = TIERS.filter(([trigger, name]) => dd >= trigger && !known.includes(name));
    const release = newTiers.reduce((sum, [, , grade]) => sum + LADDERS[ticker] * grade / 10, 0) * input.nav;
    const amount = Math.min(release, remainingCash, remainingGaps[ticker]);
    if (amount > 0) { drawdown[ticker] = amount; consumed[ticker] = newTiers.map(([, name]) => name); remainingCash -= amount; }
  }
  return {
    status: issues.length ? "DATA INCOMPLETE" : "PASS", blocking_issues: issues,
    weights: { ...Object.fromEntries(TICKERS.map(t => [t, input.positions[t] / input.nav])), cash: input.cash / input.nav },
    gaps, routine_dca: { amount: d, allocation: routine },
    strategic_baseline: { surplus, amount: baselineAmount, allocation: baseline },
    drawdown_deployment: { evaluated: drawdownFresh, allocation: drawdown, consumed_tiers: consumed },
    final_cash: remainingCash,
    execution_authorized: false, runtime_data_persisted: false
  };
}
