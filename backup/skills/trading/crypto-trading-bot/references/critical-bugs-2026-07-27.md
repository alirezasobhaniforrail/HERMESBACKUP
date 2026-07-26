# Critical Bugs Found — 2026-07-27

## Summary
5 devastating bugs were found in `backtest_final_fixed.py` that inflated ALL previous results by 88%.

## Bug Details

### Bug #1: PnL Base (Line 294)
- **Before**: `total_pnl = balance - 500`
- **After**: `total_pnl = balance - 1000`
- **Impact**: Added $500 fake profit to every backtest

### Bug #2: Monte Carlo Equity (Line 326)
- **Before**: `equity = 500; peak = 500`
- **After**: `equity = 1000; peak = 1000`
- **Impact**: MC results were inflated, profitable threshold wrong

### Bug #3: Annual Return (Line 461)
- **Before**: `annual = (total_pnl / 500) / 5.5 * 100`
- **After**: `annual = (total_pnl / 1000) / 5.5 * 100`
- **Impact**: Annual return was doubled

### Bug #4: Look-ahead Bias (Line 109)
- **Before**: `j4 = int((ts - four_h_times[0]) / 14400000)`
- **After**: Iterate backwards to find last closed 4H candle
- **Impact**: Strategy used future 4H data for 1H decisions

### Bug #5: Max Position (Line 277)
- **Before**: `max_position_value = balance * 0.15` (but header said 5%)
- **After**: Corrected to match documentation
- **Impact**: Position sizing mismatch

## Results Comparison

| Metric | Before (WRONG) | After (CORRECT) | Change |
|--------|----------------|-----------------|--------|
| Total PnL | $+10,799 | $+1,336 | -88% |
| Annual Return | +196% | +24% | -88% |
| Win Rate | 89% | 79% | -10% |
| Profit Factor | 7.23 | 2.98 | -59% |
| Trades | 2,545 | 1,466 | -42% |
| Max DD | 4.1% | 2.6% | -37% |

## Corrected Configuration
```python
# $1,000 Account | 3x Leverage | 1.5% Risk
SETTINGS = {
    'balance': 1000,
    'leverage': 3,
    'risk_per_trade': 0.015,
    'max_position_pct': 0.15,
    'tp_atr_mult': 2.0,
    'sl_atr_mult': 1.0,
    'kill_switch_dd': 20.0,
}
```

## Lessons Learned
1. **Always verify PnL base matches starting balance**
2. **Always verify MC starts from same equity as backtest**
3. **Always verify multi-timeframe alignment uses closed candles only**
4. **Run adversarial code review ("prove this is WRONG")**
5. **Trust no backtest without auditing the code itself**
