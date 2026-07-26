# Forensic Quant Audit Framework

26-section audit for validating crypto trading strategy backtests. Use BEFORE paper trading.

## Audit Sections

### 1. Look-ahead Bias
- Check ALL indicator calculations for future data leakage
- Verify HTF indicators use only CLOSED candles
- Check trailing stop intrabar timing
- Verify rolling windows don't peek forward

### 2. Data Leakage
- Feature/Target/Temporal/Cross-sectional leakage
- Train/Test contamination
- Optimization leakage (parameters tuned on same data)

### 3. Overfitting
- # parameters optimized vs # trades
- WR > 80% = suspicious (most professional: 45-65%)
- PF > 5 = suspicious (most professional: 1.5-3.0)
- DD < 5% with leverage = suspicious
- Monte Carlo 100% profitable = too good

### 4. Statistical Significance
- Confidence Interval for WR (95%)
- PF Confidence Interval
- Expectancy = (WR × Avg Win) - (LR × Avg Loss)
- Sharpe/Sortino/Calmar Ratios
- Risk of Ruin calculation
- Trade Independence check

### 5. Data Quality
- Source: Exchange-specific or aggregated?
- Spot or Futures?
- Missing data/gaps?
- Funding rate included?
- Maker/Taker fees?

### 6. Execution Realism
- Entry/Exit fills at exact price? (always NO)
- Slippage model realistic?
- Latency modeled?
- Partial fills modeled?

### 7. SL/TP Ordering
- If both SL and TP hit in same candle, which triggers first?
- OHLC doesn't capture intrabar sequence
- This can SIGNIFICANTLY change results

### 8. Regime Dependency
- Break results by: Bull/Bear/Range/HighVol/LowVol/Crash
- If only works in one regime = serious risk

### 9. Out-of-Sample
- True OOS: optimize on period A, test on period B
- OOS Ratio: Test/Train performance (target >70%)

### 10. Walk-Forward
- Rolling windows with re-optimization
- Check: WR stability, PF stability, DD stability
- All windows must be profitable

### 11. Monte Carlo
- Shuffle trades 1000+ times
- Perturb entry/exit by ±0.1%
- Model correlated losses
- Check: Median, 5th/95th percentile, worst DD

### 12. Parameter Sensitivity
- Test each parameter ±10-20%
- If only exact value works = overfitting
- If plateau of good values = robust

### 13. Stress Test
- Fee × 1.5, 2.0, 3.0
- Slippage × 1.5, 2.0
- WR degradation 5%, 10%, 15%, 20%
- Find: at what point does Edge disappear?

### 14. Crypto-Specific Risks
- Funding Rate spikes
- Liquidation risk
- Exchange outages
- API failures
- Mark Price vs Last Price

### 15. Cross-Asset Robustness
- Is profit from one coin or distributed?
- All pairs must be independently profitable

### 16. Correlation
- Simultaneous positions = aggregate risk
- During crashes: all crypto correlates to 1.0

### 17. Capital Scaling
- Test at $100, $1K, $10K, $50K, $100K
- Liquidity/Slippage impact at each level

### 18. PF Definition
- PF = Gross Profit / Gross Loss
- PF = 7.23 does NOT mean "every $1 risked = $7.23 profit"
- It means total wins / total losses

### 19. Win Rate vs Risk/Reward
- Payoff Ratio = Avg Win / Avg Loss
- If Payoff < 1: strategy depends ENTIRELY on high WR
- Expectancy must be positive after all costs

### 20. Monthly Analysis
- Average/Median/Worst/Best month
- Consecutive losing months
- Monthly Std Dev

### 21. Drawdown Analysis
- Equity DD or Balance DD?
- Closed or Intratrade DD?
- Includes slippage/fees/funding?
- Max DD Duration and Recovery Time

### 22. Backtest vs Live Gap
- Rank all degradation factors
- Typical: backtest loses 30-50% to reality

### 23. Paper Trading Protocol
- Duration: 3-6 months minimum
- Minimum 200 trades
- Minimum 2 market regimes
- Track: all metrics vs backtest
- Pass criteria: within 30% of backtest

### 24. Pass/Fail Table
| Test | Criteria | Status |
|------|----------|--------|
| Look-ahead | Zero | ? |
| Data Leakage | Zero | ? |
| OOS | >70% retention | ? |
| Walk-Forward | All windows profitable | ? |
| PF | >1.5 after costs | ? |
| Max DD | <20% | ? |
| MC Profitable | >80% | ? |
| Parameter Sensitivity | Plateau (not spike) | ? |

### 25. Scoring (out of 100)
- Data Integrity: 20
- Statistical Robustness: 15
- OOS Validation: 15
- Overfitting Resistance: 15
- Execution Realism: 10
- Regime Robustness: 10
- Risk Management: 5
- Parameter Stability: 5
- Live Deployability: 5

### 26. Verdict
- GREEN: Ready for Paper Trading
- YELLOW: Promising but unproven
- ORANGE: Likely overfit
- RED: Do not deploy

## Key Red Flags
- WR > 85% (suspiciously high)
- PF > 5 (suspiciously high)
- DD < 5% with leverage (unrealistic)
- MC 100% profitable (too good)
- Payoff Ratio < 1 (fragile)
- Only 1 bear market tested

## Our Session Results (2026-07-27)
- Score: 52/100
- Verdict: B — Promising but Unproven
- Main issue: Payoff Ratio 0.87 (losses > wins)
- Strong: Walk-Forward 8/8 profitable
- Recommendation: Paper Trade with strict monitoring
