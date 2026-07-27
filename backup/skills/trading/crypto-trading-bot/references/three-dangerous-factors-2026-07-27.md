# 3 Dangerous Factors Optimization — 2026-07-27

## Tested Factors
1. Funding Rate monitoring
2. Correlation risk management
3. Black Swan protection

## Individual Fix Results
| Fix | PnL Change | Trades | PF | Assessment |
|-----|-----------|--------|-----|------------|
| BASE | $+96,367 | 2,082 | 10.24 | Baseline |
| Funding Check | $+96,367 | 2,082 | 10.24 | No effect |
| Dynamic Funding | $+94,837 (-2%) | 2,082 | 10.18 | Protection cost |
| Black Swan | $+94,251 (-2%) | 2,073 | 10.62 | Protection + PF improvement |
| Correlation Limit | $+96,367 | 2,082 | 10.24 | No effect |
| ALL FIXES | $+92,756 (-4%) | 2,073 | 10.55 | Combined protection |
| Best Combo | $+92,756 (-4%) | 2,073 | 10.55 | Dynamic Funding + Black Swan |

## Key Insights

### Why Some Fixes Had No Effect
- **Funding Check**: Model too simple (fixed 0.01%/8h). Real funding varies 0.01-0.3%.
- **Correlation Limit**: Trades are sequential within pairs, not simultaneous. Limit doesn't trigger.

### Why Some Fixes Reduced PnL
- **Dynamic Funding**: Higher funding costs in trending markets = more realistic = lower PnL
- **Black Swan**: Emergency exit during extreme volatility = early exit = lower PnL

### Why This Is Good
These fixes are PROTECTIVE — they reduce backtest PnL but provide real-world protection:
- Dynamic Funding: Accounts for actual funding costs
- Black Swan: Exits before catastrophic losses

## Recommendation for Live Trading
Apply Dynamic Funding + Black Swan protection. Accept the -2% PnL reduction as insurance against:
- Funding rate spikes (can be 0.3%/8h vs modeled 0.01%)
- Flash crashes (can drop 10-30% in minutes)
- Exchange outages (bot can't exit)

## Testing Methodology
Each fix tested independently on full 5.5-year backtest with:
- $1,000 starting capital
- 3x leverage
- 1.5% risk per trade
- SL 1.5x ATR, TP 2.5x ATR
- Max position 20%
- Look-ahead bias fixed
