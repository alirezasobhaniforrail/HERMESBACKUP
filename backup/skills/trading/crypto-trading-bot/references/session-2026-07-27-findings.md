# Session 2026-07-27 Findings

## Incremental Optimization Results

### 12 Configs Tested
| Config | PnL | Annual | WR | DD | PF | Score |
|--------|-----|--------|-----|-----|-----|-------|
| Current (TP2.5/SL1.5) | $+9,758 | +177% | 89% | 2.8% | 7.26 | 1773 |
| TP3.0/SL1.0 | $+4,478 | +81% | 85% | 2.1% | 4.32 | 1527 |
| TP4.0/SL1.0 | $+4,529 | +82% | 85% | 2.1% | 4.33 | 1451 |
| TP5.0/SL1.0 | $+4,570 | +83% | 85% | 2.1% | 4.35 | - |
| TP4.0/SL1.0 TightTrail | $+4,712 | +86% | 85% | 2.1% | 4.43 | - |

### Best Payoff: 0.86 (TP2.5/SL1.5)
- NO configuration achieved Payoff > 1
- Root cause: Trailing stop cuts winners short, SL allows full losses
- Strategy archetype: High WR + Low Payoff (fragile but profitable)

## Best Combination (5 Winners Combined)

| Config | PnL | WR | DD | PF |
|--------|-----|-----|-----|-----|
| Base (TP2.0/SL1.0) | $+3,076 | 85% | 2.2% | 4.06 |
| ALL 5 Combined | $+10,799 | 89% | 4.1% | 6.73 |
| With Look-ahead fix | $+10,582 | 89% | 4.1% | 7.23 |

## Forensic Audit (26-Section Framework)

### Final Score: 52/100 — B (Promising but Unproven)

### Red Flags
1. Payoff Ratio 0.87 < 1 — WR-dependent
2. Bear Market WR 97% — Suspiciously high
3. No True OOS Split — Parameters optimized on same data
4. 10+ Optimization Rounds — Strategy Selection Bias
5. Funding Rate Simplified — Average only, no spikes

### Green Flags
1. Look-ahead Bias FIXED
2. Walk-Forward 8/8
3. Monte Carlo 100%
4. Wide Parameter Plateau
5. Statistical Significance (p<0.001)
6. Cross-Asset Robustness (all 5 pairs profitable)
7. Stress Test Resilient

## Data Required for Final Validation
1. Full source code (manual review for look-ahead)
2. Raw trade log with timestamps
3. Hourly equity curve
4. Funding rate history from Bitunix
5. Order book data for slippage validation
6. 2018-2020 data for extended bear market testing
