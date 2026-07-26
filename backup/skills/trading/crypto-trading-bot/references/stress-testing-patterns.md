# Stress Testing Patterns for Crypto Trading Strategies

## Why Stress Test?

Backtest results are MEANINGLESS without stress testing. A strategy that shows +4000% on historical data can be:
- Overfitted to past patterns
- Only works in one market regime
- Breaks with realistic fees/slippage
- Destroys your account in worst-case scenarios

## The 8-Test Framework

### Test 1: Walk-Forward Rolling
```
Split data into 4+ windows of 1.3yr train / 0.5yr test
Slide forward, retrain, test on unseen data
All test windows must be profitable
If 2+ windows lose money → STRATEGY IS OVERFITTED
```

### Test 2: Out-of-Sample
```
Train: 2021-2023 (3 years)
Test: 2024-2026 (unseen data)
Calculate: test_pnl / train_pnl ratio
If ratio < 0.3 → SEVERE OVERFITTING
If ratio 0.3-0.6 → MODERATE OVERFITTING
If ratio > 0.6 → ROBUST
```

### Test 3: Monte Carlo
```python
# Shuffle trade sequence 1000 times
# Each shuffle represents a different order of same trades
# Check: What's the worst case if bad trades come first?

for _ in range(1000):
    shuffled = trade_pnls[:]
    random.shuffle(shuffled)
    equity = initial
    max_dd = 0
    killed = False
    for pnl in shuffled:
        # Apply risk decay after consecutive losses
        if consec_losses >= 3:
            pnl *= 0.25  # 75% reduction
        equity += pnl
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
        if dd > kill_threshold:  # Dynamic threshold
            killed = True
            break
        consec_losses = consec_losses + 1 if pnl <= 0 else 0
    results.append({'final': equity, 'max_dd': max_dd, 'killed': killed})

# CRITICAL METRICS:
# - killed_pct: % of sims that hit kill switch (MUST be <20%)
# - profitable_pct: % of sims profitable (MUST be >80%)
# - worst_dd: Worst max DD across all sims
# - p95_dd: 95th percentile DD (worst 5% of scenarios)
# - 95% CI of final equity
```

**Kill Switch Optimization**: If killed_pct > 20%, reduce risk_per_trade by 50% and re-test. This single change typically drops kills from 60%+ to 0%.

### Test 4: Regime Analysis
```
Tag each trade with regime: BULL / BEAR / RANGE
Calculate WR and PnL per regime
Strategy MUST be profitable in all 3 regimes
If only profitable in BULL → WILL FAIL in bear market
```

### Test 5: Fee Sensitivity
```
Test with 0.5x, 1x, 2x, 3x, 5x normal fees
Strategy must remain profitable at 3x fees
If breaks at 2x → edge is too thin for real trading
```

### Test 6: Slippage Stress
```
Add extra 0.1-0.2% cost per trade
Simulates: market orders during volatility, partial fills
If strategy breaks → need limit orders or wider exits
```

### Test 7: Consecutive Loss Survival
```
Report max consecutive losses per pair
If max > 5 → position sizing too aggressive
Calculate: what account size survives this streak?
```

### Test 8: Worst Month Analysis
```
Show worst 3 months across all pairs
If any month loses >20% of account → too risky
If worst months are >$100 on $500 → scale down risk
```

## Overfitting Detection Checklist

| Signal | Healthy | Overfitted |
|--------|---------|------------|
| Walk-Forward windows profitable | >80% | <60% |
| Out-of-Sample ratio | >60% of train | <30% of train |
| Monte Carlo profitable | >85% of sims | <70% of sims |
| Win rate | 60-85% | >90% or <40% |
| Profit factor | >1.5 | >5.0 (suspicious) |
| Max DD | <20% | >30% |
| Trades per month | 3-8 | <1 or >20 |
| Regime performance | Profitable all | Only one regime |

## Risk Management Rules

### Position Sizing
```python
risk_per_trade = 0.015  # 1.5% of equity
sl_distance = atr * sl_atr_mult
qty = (balance * risk_per_trade) / sl_distance
```

### Risk Decay
```python
if consecutive_losses >= 3:
    risk_multiplier = 0.5  # Cut risk by 50%
    # Or: pause trading for 48 bars (2 days at 1H)
```

### Kill Switch
```python
if (peak_equity - current_equity) / peak_equity > 0.15:
    # Stop all trading
    # Close all positions
    # Alert user
```

### Cooldown
```python
# After ANY position closes:
cooldown[pair] = now + timedelta(hours=4)

# Before opening new position:
if pair in cooldown and now < cooldown[pair]:
    continue  # Skip this pair
```

## Common Failure Modes

1. **Correlation Death**: All crypto pairs drop together → portfolio DD spikes
   - Fix: Max 3 positions, cluster correlation check

2. **Regime Blindness**: Strategy only works in trending market
   - Fix: Test separately in BULL/BEAR/RANGE

3. **Fee Erosion**: Edge exists but fees eat all profit
   - Fix: Test with 3x fees, require PF > 2.0

4. **Psychological Blowup**: 50%+ DD makes trader quit
   - Fix: Kill switch at 15%, risk decay after losses

5. **Execution Gap**: Backtest assumes instant fills
   - Fix: Add 0.1% slippage stress test

6. **Curve Fitting**: Complex strategy fits noise, not signal
   - Fix: Walk-forward validation, out-of-sample testing
