# Market Data Sources

## Purpose

Market environment data for Investment OS. Data is descriptive only unless promoted through a versioned rule change.

## Sources

| Field | Source | Status |
|---|---|---|
| VIX Index | Cboe VIX official | Green |
| US 10Y Treasury Yield | Federal Reserve FRED | Green |
| DXY Dollar Index | Pending source validation | Yellow |
| Nasdaq-100 Valuation | Pending validation | Red |

## Rules

- No value without source and timestamp.
- Missing data is recorded as N/A, never replaced with old values.
- Red data cannot enter Production decisions.
