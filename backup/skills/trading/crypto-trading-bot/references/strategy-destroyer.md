# Strategy Destroyer — Hostile Critic Methodology

## Purpose
Find EVERY flaw before paper trading. This is NOT about validating the strategy — it's about trying to DESTROY it.

## The 9 Flaws

### 1. Ideal vs Realistic Costs
Test with multiple fee levels:
- Ideal: 0.03% slippage
- Realistic: 0.05% slippage
- Worst Case: 0.10% slippage

### 2. Realistic Fills
SL doesn't always fill at exact price:
```python
# During high volatility, fill might be WORSE than SL
slippage_extra = 0.001 if atr_pct > avg_vol * 1.5 else 0
exit_price = sl * (1 - slippage_extra)  # Fill worse than SL
```

### 3. Correlation Between Pairs
Count months where 2+ pairs lose simultaneously.

### 4. Signal Quality Over Time
Split data in half — do signals degrade in later years?

### 5. Win/Loss Streaks
Can you survive the worst streak? Calculate max loss at current risk.

### 6. Drawdown Duration
How long do you stay in drawdown? (trades × avg hold time)

### 7. Monthly Consistency
Target: ≥80% profitable months.

### 8. Realistic Slippage Model
Fixed 0.03% is a fantasy. Real: 0.05-0.10%. Flash crash: 1-5%.

### 9. Behavioral Reality
Humans can't follow rules — expect 30-50% degradation.

## Expected Degradation
Real Return = Backtest Return × (0.4 to 0.6)

## Red Flags
- Strategy only works in ONE regime
- Win rate >90% (likely curve-fitted)
- DD duration >30 days
- Monthly consistency <70%
- Realistic fills reduce performance by >50%
