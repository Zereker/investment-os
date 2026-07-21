# Investment OS Operating Model

## System Layers

### 1. Investment OS
Long-term principles and decision rules. Updated rarely, normally every six to twelve months or after a major strategic review.

### 2. Portfolio Playbook
Current portfolio strategy, security-level theses, capital-allocation rules, and watchlist policy. Reviewed quarterly or when fundamentals materially change.

### 3. IBKR Snapshot
Dynamic portfolio state: positions, cash, orders, cost basis, concentration, and temporary price triggers. Updated during each cruise.

### 4. Review Log
A permanent record of proposed trades, completed trades, no-action decisions, lessons, and policy changes.

## Cruise Workflow

When the command `巡航 IBKR` is used, the review follows this sequence:

1. Investment OS compliance
2. Playbook compliance
3. Snapshot update
4. Risk Radar
5. Trade or no-trade review
6. Final status: Execute, Wait, or Reject
7. Archive the result under `reviews/`

## Change Governance

- Dynamic facts update the Snapshot.
- Security-level strategy changes update the Playbook.
- Long-term principles require an explicit Investment OS version change.
- No temporary market price should silently become a permanent rule.

## Second-Opinion Mechanism

Every active trade requires a documented second opinion before execution. This mechanism is tool-independent and may be satisfied by:

- AI review
- Written investment journal review
- Delayed overnight review
- Formal peer review

## Default Decision

When evidence does not establish that a trade is superior to continued holding, the default decision is no action.