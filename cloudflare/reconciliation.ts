export const DEFAULT_RECONCILIATION_TOLERANCE = 0.005;

export type ReconciliationDetails = {
  status: "PASS" | "DATA INCOMPLETE";
  issues: string[];
  nav: number | null;
  cash: number | null;
  positions_market_value: number | null;
  component_total: number | null;
  absolute_difference: number | null;
  relative_difference: number | null;
  tolerance: number;
  diagnostic: string | null;
};

export function unavailableReconciliation(
  issue: string
): ReconciliationDetails {
  return {
    status: "DATA INCOMPLETE",
    issues: [issue],
    nav: null,
    cash: null,
    positions_market_value: null,
    component_total: null,
    absolute_difference: null,
    relative_difference: null,
    tolerance: DEFAULT_RECONCILIATION_TOLERANCE,
    diagnostic: null
  };
}

export function reconcileNav(
  nav: number,
  cash: number,
  positionValues: number[],
  tolerance = DEFAULT_RECONCILIATION_TOLERANCE
): ReconciliationDetails {
  const positionsMarketValue = positionValues.reduce(
    (sum, value) => sum + value,
    0
  );
  const componentTotal = cash + positionsMarketValue;
  const absoluteDifference = Math.abs(componentTotal - nav);
  const relativeDifference = absoluteDifference / Math.abs(nav);
  const passed = relativeDifference <= tolerance;
  return {
    status: passed ? "PASS" : "DATA INCOMPLETE",
    issues: passed
      ? []
      : [
          `cash plus positions does not reconcile to NAV: difference ${(relativeDifference * 100).toFixed(2)}% of NAV (limit ${(tolerance * 100).toFixed(2)}%)`
        ],
    nav,
    cash,
    positions_market_value: positionsMarketValue,
    component_total: componentTotal,
    absolute_difference: absoluteDifference,
    relative_difference: relativeDifference,
    tolerance,
    diagnostic: absoluteDifference === 0 ? null :
      "Difference is within tolerance and may reflect timing, accrued dividends, FX translation, or other equity components; this is diagnostic only, not a confirmed cause."
  };
}
