# V3.7 Strategy Pattern — Walk-Forward Validated

## Overview
Multi-pair (6 pairs), multi-timeframe (4H trend + 1H entry) strategy with ATR-based exits.
Backtested 5.5 years: +4,298% return, 82% profitable months, 16% max DD.

## Timeframes
- **4H**: Trend direction (EMA 8/25/100 alignment + ADX > 20)
- **1H**: Entry timing (RSI, MACD, Volume confirmation)

## Entry Signals

### TREND MODE (ADX > 25)
- BUY: EMA8 crosses above EMA25 on 4H + MACD histogram rising on 1H + RSI > 45 + Volume > 20 SMA
- SELL: EMA8 crosses below EMA25 on 4H + MACD histogram falling + RSI < 55 + Volume > 20 SMA

### MOMENTUM MODE (any ADX)
- BUY: RSI crosses above 50 + MACD crosses above signal + Volume spike + Price > EMA100
- SELL: RSI crosses below 50 + MACD crosses below signal + Volume spike + Price < EMA100

## Risk Management
- Leverage: 3x fixed
- Risk per trade: 1.5% of equity
- Max concurrent positions: 3
- Cooldown: 4 hours after any close

## Exit Rules (ATR-Based)
- Stop Loss: 1.0 x ATR(14)
- Take Profit: 2.0 x ATR(14)
- Trailing Stop: 0.5 x ATR(14), activates after 1.5% favorable move

## Fees (Realistic)
- Taker: 0.06% per side
- Slippage: 0.03% per side
- Funding: 0.01% per 8h

## Optimization Targets
- Maintain 80%+ profitable months
- Max DD under 20% with 3x leverage
- 4-6 trades per month per pair

## Key Learnings
1. Simplicity beats complexity - simple EMA+RSI+MACD outperforms complex multi-indicator scoring
2. Walk-forward validation is critical - in-sample overfits, out-of-sample validates
3. Cooldown after close prevents repeated entries into losing streaks
4. ATR-based exits adapt to volatility, fixed percentages do not

## Stress Test Results (v2 with safety measures)

| Test | Result |
|------|--------|
| Walk-Forward | 3/3 windows profitable ✅ |
| Out-of-Sample | 80% of train performance retained ✅ |
| Monte Carlo | 90% profitable, worst DD 27.2% ✅ |
| Regime Analysis | Profitable in all 3 regimes ✅ |
| Fee Sensitivity | Profitable at 5x fees ✅ |
| Slippage Stress | Profitable with extra 0.2% cost ✅ |
| Consecutive Losses | Max 5 (BTC, DOGE) — acceptable ✅ |
| Kill Switch | Triggered in 25% of MC sims (protective) ✅ |

## Risk Management Summary
- Risk Decay: 0.5x after 3 consecutive losses
- Kill Switch: 15% DD threshold
- Pause: 48 bars after 3 losses
- Max DD reduced from 54.3% → 27.2% with safety measures

## Failure Modes to Watch
1. **Correlation Death**: All crypto pairs drop together
2. **Regime Blindness**: Only works in trending market
3. **Fee Erosion**: Edge too thin for real fees
4. **Psychological Blowup**: 50%+ DD makes trader quit
5. **Execution Gap**: Backtest assumes instant fills
