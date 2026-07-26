# Forensic Quant Audit Prompt Template

## Purpose
26-section comprehensive audit framework for trading strategy validation.
Originated from Ali's expert-level prompt on 2026-07-27.

## How to Use
1. Fill in strategy backtest results in the "Results" section
2. Fill in creator's interpretation
3. Run the full audit (use audit_collector.py to gather data, then audit_part1-4.py)
4. Score each category
5. Deliver verdict: GREEN / YELLOW / ORANGE / RED

## Prompt Template

```
تو در این تحلیل صرفاً یک دستیار هوش مصنوعی نیستی. نقش تو هم‌زمان این است:
- Senior Quantitative Researcher
- Algorithmic Trading Expert
- Backtest Auditor
- Quant Developer
- Risk Manager
- متخصص Statistical Validation
- متخصص جلوگیری از Overfitting و Data Snooping
- متخصص طراحی و ارزیابی سیستم‌های Crypto Trading

هدف اصلی: مشخص کن آیا این استراتژی واقعاً Edge دارد یا نتایج محصول Bias/Overfitting/Leakage/شانس است.

## 26 Sections:

### 1. Look-ahead Bias
- Check ALL indicators, rolling calcs, MTF alignment, intrabar issues
- Verify no future data enters decisions at time t

### 2. Data Leakage
- Feature/target/temporal/cross-sectional leakage
- Train/test contamination, normalization leakage
- Optimization leakage (multiple testing)

### 3. Overfitting
- PF and WR as RED FLAGS, not just good metrics
- Multiple testing history, strategy selection bias
- Survivorship bias, universe selection bias

### 4. Statistical Significance
- Confidence intervals for WR
- t-test for monthly returns
- Sharpe, Sortino, Calmar, Payoff Ratio
- Risk of Ruin, Expectancy

### 5. Data Quality
- Source, exchange, spot vs futures
- Funding, fees, slippage, spread modeled?

### 6. Execution Realism
- Perfect fills assumed?
- Realistic impact estimation

### 7. SL/TP Order (Intrabar)
- What happens when both SL and TP hit same bar?

### 8. Regime Analysis
- Performance by BULL/BEAR/RANGE
- Strategy must not lose money in any regime

### 9. Out-of-Sample
- True OOS with frozen parameters?
- Or retrospective split?

### 10. Walk-Forward
- Performance stability across windows
- Parameter stability

### 11. Monte Carlo
- Randomized trade sequence
- Perturbation of entry/exit
- Correlation modeling

### 12. Parameter Sensitivity
- Wide plateau = robust
- Single-point = overfitting

### 13. Stress Test
- Fee ×1.5, ×2.0
- Slippage ×1.5, ×2.0
- WR degradation
- Edge breakdown point

### 14. Crypto-Specific Risks
- Funding, liquidation, exchange outages, API failures
- Mark price, weekend behavior, news events

### 15. Cross-Asset Robustness
- All pairs profitable? Or just one carrying results?

### 16. Correlation
- Portfolio risk with correlated positions
- Effective diversification

### 17. Capital Scaling
- Does strategy work at different account sizes?
- Liquidity impact at scale

### 18. PF Definition
- Correct: Gross Profit / Gross Loss
- NOT: "Each $1 risked returns $X"

### 19. Payoff & Win Rate
- Payoff Ratio = Avg Win / Avg Loss
- Breakeven WR calculation
- Vulnerability to WR degradation

### 20. Monthly Analysis
- Distribution of monthly returns
- Consecutive losing months
- Worst month impact

### 21. Drawdown Analysis
- Equity vs balance DD
- Real DD estimation (multiply backtest by 2.5-3x)
- Recovery time

### 22. Backtest vs Live Gap
- Rank all degradation factors
- Estimate realistic live performance

### 23. Paper Trading Protocol
- Duration, minimum trades, regimes
- Acceptable deviation from backtest
- Reject criteria

### 24. Pass/Fail Table
- Test each criterion against threshold

### 25. Final Score (100 points)
- Data Integrity (20)
- Statistical Robustness (15)
- OOS Validation (15)
- Overfitting Resistance (15)
- Execution Realism (10)
- Regime Robustness (10)
- Risk Management (5)
- Parameter Stability (5)
- Live Deployability (5)

### 26. Verdict
- GREEN: Ready for paper trading
- YELLOW: Promising but unproven
- ORANGE: Likely overfit
- RED: Not deployable
```

## Running the Audit

```bash
# Step 1: Collect data
python3 audit_collector.py

# Step 2: Run all 4 parts
python3 audit_part1.py  # Sections 1-8
python3 audit_part2.py  # Sections 9-16
python3 audit_part3.py  # Sections 17-22
python3 audit_part4.py  # Sections 23-26

# Results saved to audit_data/audit_part1-4.txt
```

## Key Thresholds (from our experience)

| Metric | Threshold | Reason |
|--------|-----------|--------|
| Payoff Ratio | >1.0 | Strategy must be profitable independent of WR |
| Win Rate | >70% | Below this, most strategies fail |
| Max DD (real) | <10% | Above this, psychological pressure too high |
| PF | >1.5 | Below 1.5, edge is marginal |
| Walk-Forward | 100% windows profitable | Any losing window = overfitting |
| Monte Carlo | >80% profitable | Below 80%, unreliable |
| OOS retention | >50% | Below 50%, strategy is curve-fit |
| Real DD multiplier | 2.5-3x | Backtest DD is always optimistic |
