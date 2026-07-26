# Incremental Optimization Results (2026-07-26)

## Methodology
Test each fix separately against BASE config. Keep if PnL improves, discard if worsens.

## BASE Config
```python
BASE = {
    'tp_atr': 2.0, 'sl_atr': 1.0, 'leverage': 3,
    'kill_dd': 20.0, 'default_risk': 0.015, 'max_position_pct': 0.15,
}
# Result: $+3,076 (+56% annual, 85% WR, 2.2% DD, PF 4.06)
```

## All 18 Configs Tested

| Config | PnL | Annual | WR | DD | PF | Score | Verdict |
|--------|-----|--------|-----|-----|-----|-------|---------|
| BASE (no fixes) | $+3,076 | +56% | 85% | 2.2% | 4.06 | 1394 | Baseline |
| + Time Filter | $+1,359 | +25% | 79% | 2.6% | 3.03 | 515 | ❌ -57% |
| + Vol Filter | $+3,005 | +55% | 85% | 2.2% | 4.12 | 1361 | ≈ same |
| + Funding Check | $+2,577 | +47% | 85% | 2.2% | 4.11 | 1168 | ❌ -16% |
| + Bear Extra | $+3,240 | +59% | 85% | 2.2% | 4.19 | 1468 | ✅ +5% |
| + BB Filter | $+1,182 | +21% | 81% | 1.5% | 3.33 | 793 | ❌ -62% |
| + Slippage Model | $+3,192 | +58% | 85% | 2.2% | 4.20 | 1451 | ✅ +4% |
| + Funding Model | $+3,076 | +56% | 85% | 2.2% | 4.06 | 1394 | ≈ same |
| + Time Stop | $+3,068 | +56% | 84% | 2.2% | 4.05 | 1390 | ≈ same |
| + 2x Leverage | $+3,076 | +56% | 85% | 2.2% | 4.07 | 1394 | ≈ same |
| + Max Pos 10% | $+1,880 | +34% | 85% | 1.5% | 4.05 | 1276 | ❌ -39% |
| + Max Pos 20% | $+4,488 | +82% | 85% | 2.9% | 4.08 | 1527 | ✅ +46% |
| + Risk 1% | $+3,075 | +56% | 85% | 2.2% | 4.06 | 1393 | ≈ same |
| + Risk 2% | $+3,076 | +56% | 85% | 2.2% | 4.06 | 1394 | ≈ same |
| + TP 1.5x | $+3,030 | +55% | 85% | 2.2% | 4.03 | 1373 | ≈ same |
| + TP 2.5x | $+3,128 | +57% | 84% | 2.2% | 4.09 | 1417 | ✅ +2% |
| + SL 0.5x | $+901 | +16% | 77% | 1.4% | 2.27 | 664 | ❌ -71% |
| **+ SL 1.5x** | **$+6,170** | **+112%** | **89%** | **3.5%** | **6.25** | **1773** | **✅ +101%** |

## Winner Combination
```python
BEST = {
    'tp_atr': 2.5,      # Was 2.0
    'sl_atr': 1.5,      # Was 1.0 — BIGGEST winner
    'leverage': 3,
    'max_position_pct': 0.20,  # Was 0.15
    'bear_extra': True,
    'slippage_model': True,
}
# Result: $+10,799 (+196% annual, 89% WR, 4.1% DD, PF 6.73)
```

## Combination Pitfall
Combining ALL 7 "good" fixes (including Time Filter, BB Filter) yielded only $+672.
**Some fixes conflict — always test combinations, not just individual fixes.**

## Key Takeaways
1. SL width is the single biggest lever (wider SL = fewer false stops)
2. "Safety" measures often hurt performance
3. BB filter in RANGE is too restrictive
4. Session filter removes good signals
5. Always test each fix independently before combining
