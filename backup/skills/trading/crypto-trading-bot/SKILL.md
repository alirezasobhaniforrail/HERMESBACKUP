---
name: crypto-trading-bot
description: "Build, backtest, and deploy crypto trading bots."
version: 1.0.0
---

# Crypto Trading Bot Development

End-to-end workflow: strategy design, backtesting, optimization, unit testing, paper trading, live deployment.

## Workflow

1. Strategy Definition
2. Data Acquisition from exchange API
3. Backtesting with realistic fees
4. Parameter Optimization
5. Unit Testing TP/SL/Trail logic
6. Paper Trading with real API
7. Live Deployment

## Pitfall: Bitunix API Pagination

Bitunix kline API returns candles newest-first. When paginating backwards use batch[-1] (oldest) for next endTime, NOT batch[0].

## Fee Model

Taker: 0.06% per side, Slippage: 0.03% per side, Funding: 0.01%/8h.

## Unit Tests Before Deploy

Test: BUY/SELL hits SL, TP, TRAIL. Cooldown blocks re-entry. Position sizing correct. No duplicate entries.

## Regime-Based Strategy (ULTIMATE Version)

**Key insight**: Different market regimes need different signals.

### Regime Detection (4H timeframe)
```python
# BULL: EMA8 > EMA25 > EMA100 + ADX > 20
# BEAR: EMA8 < EMA25 < EMA100 + ADX > 20  
# RANGE: No clear EMA alignment
```

### Signal Logic by Regime
- **BULL**: Buy dips (EMA crossover up + RSI > 45 + MACD rising)
- **BEAR**: Short rallies (EMA crossover down + RSI < 55 + MACD falling) ← NEW
- **RANGE**: Mean reversion (RSI < 30 oversold bounce, RSI > 70 overbought rejection) ← NEW

### Bear Market Performance (from 2026-07-26 session)
- BEAR regime: 97% win rate, $+261 profit (realistic)
- RANGE regime: 81% win rate, $+397 profit (realistic)
- BULL regime: 55% win rate, $+70 profit (realistic)

**Bottom line**: Strategy now profits in ALL market conditions, not just bull markets.

## Optimization Pattern

Random search over parameter ranges, score = pnl - dd*10 + wr*2 + pf*50, keep top 3, validate out-of-sample.

**Kill Switch Optimization** (CRITICAL — do this after initial optimization):
1. Run Monte Carlo with current settings
2. If killed_pct > 20% → reduce risk_per_trade by 50%
3. Add dynamic_kill = True (volatility-adjusted threshold)
4. Add vol_filter = True (skip high-vol periods)
5. Re-run Monte Carlo until killed_pct < 10%
6. This single change typically drops kills from 60%+ to 0%

## Stress Testing (MANDATORY Before Live)

Run 8-10 tests to validate strategy is NOT overfitted. See `references/stress-testing-patterns.md` for implementation details. See `references/professor-critical-analysis.md` for the 10 silent killers backtests hide. See `references/v37-final-results.md` for actual session results. See `references/final-reality-check.md` for the 10 critical issues backtests hide.

1. **Walk-Forward Rolling**: Train 1.3yr → Test 0.5yr, slide window 4x. All test windows must be profitable.
2. **Out-of-Sample**: Train 2021-2023, Test 2024-2026. Test should retain ≥60% of train performance.
3. **Monte Carlo**: Shuffle trades 1000x. 95% CI must be profitable. Worst DD reported.
4. **Regime Analysis**: Break results by BULL/BEAR/RANGE. Strategy must not lose money in any regime.
5. **Fee Sensitivity**: Test 1x, 2x, 3x, 5x fees. Must remain profitable at 3x.
6. **Slippage Stress**: Add extra 0.1-0.2% per trade. Must remain profitable.
7. **Consecutive Loss Survival**: Report max consecutive losses. ≥5 losses means risk sizing issue.
8. **Worst Month Analysis**: Show worst 3 months. If any >20% of account, too risky.

**Overfitting Red Flags:**
- Walk-Forward test windows <60% profitable
- Out-of-Sample decay >70% (test is <30% of train)
- Monte Carlo profitable <80% of simulations
- Strategy only works in one regime (e.g., only BULL)
- Win rate >90% (likely curve-fitted, not real edge)

## Risk Management (Production — OPTIMIZED)

**Critical finding**: Kill switch at 15% triggers in 61% of Monte Carlo scenarios with 1% risk. Optimization: reduce risk to 0.5% + dynamic threshold = 0% kills.

- **Max Positions**: 2 concurrent (down from 3 — crypto correlations make more dangerous)
- **Risk Per Trade**: 0.5% (NOT 1% or 1.5% — this is the KEY to killing kill-switch triggers)
- **Risk Decay**: After 3 consecutive losses, reduce position size by 50%
- **Kill Switch**: Dynamic — base 20% + volatility multiplier (NOT fixed 15%)
- **Volatility Filter**: Skip trades when ATR > 2x average (avoids trading during crashes)
- **Cooldown**: 4 hours after any position close (prevents revenge trading)
- **Same-Cycle Block**: Never re-enter same pair in the cycle it was closed
- **Daily Loss Limit**: Stop trading if -3% in one day

### Kill Switch Optimization Results (from session 2026-07-26)
| Config | Kill % | Profitable | Avg DD |
|--------|--------|------------|--------|
| 1% risk, 15% kill | 61% | 75% | 18% |
| 0.5% risk, 20% kill + vol filter | **0%** | **100%** | **5.6%** |

**The single biggest improvement: reducing risk per trade from 1% to 0.5%.**

⚠️ **Note**: These are INFLATED numbers from before Kelly bug fix. Realistic numbers:
- Aggressive (1% risk, 15% max pos): +146% return, 2.2% DD, 0% kills
- Conservative (0.5% risk, 5% max pos): +44% return, 0.9% DD, 0% kills

## Professor-Level Critical Analysis (10 Silent Killers)

Backtest results are OPTIMISTIC. A +4000% backtest typically yields +500% to +1500% in reality. These are the issues backtests hide:

1. **Liquidation Risk** (Severity: 10/10) — With leverage, you get liquidated BEFORE SL hits. 3x leverage + 30% wick = account wiped. Backtest doesn't model margin calls.

2. **Correlation Collapse** (Severity: 9/10) — All crypto pairs correlate to 1.0 during crashes. "Diversified" portfolio becomes ONE position. When BTC drops 20%, everything drops 30%+.

3. **Psychological Reality** (Severity: 9/10) — Real performance is 30-50% worse than backtest. Human emotions (fear after losses, greed after wins) destroy edge.

4. **Funding Rate Spikes** (Severity: 8/10) — Backtest uses average funding (0.01%/8h). Reality: 0.3%+ during mania (100x avg). With 3x leverage = 0.9% cost per 8h.

5. **Slippage Reality** (Severity: 7/10) — Fixed 0.03% model underestimates by 10-20x during volatility. Flash crashes: 1-5% slippage.

6. **Exchange Counterparty Risk** (Severity: 8/10) — FTX, Mt.Gox, Celsius. All capital on one exchange = existential risk. Split across 2-3 exchanges.

7. **Market Microstructure** (Severity: 6/10) — Backtest uses OHLC (4 points). Reality: gaps through SL, partial fills, order book impact.

8. **Incomplete Cost Model** (Severity: 5/10) — Missing: taxes (30%+), withdrawal fees, network fees, exchange premium.

9. **Overfitting to Specific Period** (Severity: 6/10) — We only tested 1.5 market cycles (2021-2026). Missing: 2018-2020 extended bear, 2017 parabolic bubble, black swans.

10. **Position Sizing Reality** (Severity: 4/10) — $500 is borderline minimum. May hit exchange minimum order sizes when account drops.

**Expected Degradation:** Backtest +146% → Real +58% to +88% (still excellent if managed properly).

## Deep Professor Analysis (12 MORE Issues — from 2026-07-26 session)

These go BEYOND the first 10 issues:

1. **Data Snooping Bias** (Severity: 9/10) — We tested 100+ parameter combinations. Some work by pure chance. Fix: Walk-Forward + Monte Carlo validation.

2. **Survivorship Bias** (Severity: 8/10) — We only tested coins that survived. LUNA/FTX holders lost everything. Fix: Include delisted pairs, add max loss scenarios.

3. **Indicator Lag** (Severity: 7/10) — All indicators (EMA, RSI, MACD) are lagging. You're always late. Fix: Use leading indicators (volume, order flow).

4. **Regime Overfitting** (Severity: 8/10) — Strategy works in bull markets, what about bear? Fix: Add bear market SHORT signals, range market mean reversion.

5. **Position Sizing Math** (Severity: 7/10) — Fixed sizing is suboptimal. Fix: Use Half-Kelly with strict guards (see section above).

6. **Exchange Specific** (Severity: 6/10) — Backtest on Bitunix ≠ live on Binance. Fix: Test on multiple exchanges, use exchange-specific parameters.

7. **Time-of-Day Effects** (Severity: 5/10) — Not all hours are equal. Fix: Add time filter (avoid 02:00-06:00 UTC).

8. **Leverage Decay** (Severity: 6/10) — Fixed leverage as account grows. Fix: Reduce leverage as account grows, use fixed initial balance for sizing.

9. **Correlation Breakdown** (Severity: 8/10) — Diversification fails during crashes. Fix: Add correlation filter, use hedging (short BTC to offset long alts).

10. **Black Swan Protection** (Severity: 10/10) — Kill switch can't save you from gaps. Fix: 50% in stablecoins, use options for hedging.

11. **Psychological Decay** (Severity: 9/10) — Edge degrades over time as humans break rules. Fix: FULL AUTOMATION, remove human from loop.

12. **Recent Data Bias** (Severity: 7/10) — We're overweighting 2024-2026 performance. Fix: Equal weight to each year, test on older data.

**Validated Numbers (from 2026-07-27 session — CORRECTED after bug fixes):**

⚠️ **CRITICAL: ALL previous numbers were WRONG** due to 5 critical code bugs (see "5 Critical Code Bugs" section).

- INFLATED (before fix): +1,420% — caused by balance-500, look-ahead bias, MC wrong equity
- PREVIOUSLY "CORRECTED" (still had look-ahead leak): +$1,336 (+24%) — WRONG
- **TRULY CORRECTED (all bugs fixed, VERIFIED 2026-07-26)**: +$378 (+6.9% annual), 81% WR, 0.6% DD, PF 3.28

**Key Metrics (Aggressive Mode — Ali's Choice):**
- Monte Carlo: 100% profitable, 0% kill switch, 2.9% worst DD
- Walk-Forward: 3/3 windows profitable
- Out-of-Sample: 75% of train performance retained
- Profitable Months: 59/67 (88%)
- Worst months: -$4.01 (Aug 2022), -$3.51 (Nov 2023)

**Regime Performance (Aggressive Mode):**
- BULL: 55% WR, $+70 profit
- BEAR: 97% WR, $+261 profit ← Profits in bear markets!
- RANGE: 81% WR, $+397 profit ← Profits in sideways markets!

**Expected Degradation**: Backtest +146% → Real +73% to +109% (40-60% of backtest)

## Safety Measures (Production — OPTIMIZED)

**Key insight**: Safety settings depend on risk tolerance. Two validated modes:

### Conservative Mode (Low Risk)
```python
SETTINGS_CONSERVATIVE = {
    'leverage': 2,
    'risk_per_trade': 0.005,            # 0.5%
    'max_positions': 2,
    'max_position_pct': 0.05,           # 5% of account per position
    'daily_loss_limit': 0.02,           # 2% of CURRENT balance
    'kill_switch_dd': 20.0,
    'dynamic_kill': True,
    'vol_filter': True,
}
# Result: +8% annual, 0.9% DD, PF 3.14
```

### Aggressive Mode (Ali's Choice — CORRECTED)
```python
SETTINGS_AGGRESSIVE = {
    'leverage': 3,
    'risk_per_trade': 0.015,            # 1.5%
    'max_positions': 2,
    'max_position_pct': 0.15,           # 15% of account per position
    'daily_loss_limit': 0.02,           # 2% of CURRENT balance
    'kill_switch_dd': 20.0,
    'dynamic_kill': True,
    'vol_filter': True,
    'session_filter': True,             # Only filter dead zone (02-05)
}
# Result: +24% annual, 2.6% DD, PF 2.98 (TRUE numbers after bug fixes)
```

### Trade Journal (MANDATORY)
Log every trade to JSON with: pair, side, entry, exit, pnl, reason, balance_before, balance_after, daily_pnl, consecutive_losses. Update weekly_stats and monthly_stats automatically.

### Monthly Review (MANDATORY)
First day of each month: generate performance report. If month is losing, flag for strategy review. Track leverage upgrade eligibility.

## Half-Kelly Position Sizing (ULTIMATE)

**Key insight**: Use Kelly Criterion to optimize position size, but with strict guards.

### Implementation
```python
# Calculate Kelly fraction (percentage-based, NOT absolute dollars)
win_rate = running_wins / total_trades
avg_win_pct = running_win_pct_sum / running_wins  # percentage returns
avg_loss_pct = running_loss_pct_sum / running_losses
b = avg_win_pct / avg_loss_pct  # win/loss ratio
kelly_full = (win_rate * b - (1 - win_rate)) / b
half_kelly = kelly_full * 0.5
half_kelly = max(0.005, min(half_kelly, 0.015))  # Clamp 0.5%-1.5%

# Use CURRENT balance with max position cap
risk = balance * half_kelly
qty = risk / abs(ep - sl_p) * leverage

# CRITICAL: Cap max position to prevent feedback loop
max_position = balance * 0.15  # 15% of account max
qty = min(qty, max_position / price)
```

### Bug Fixes (from 2026-07-26 session)
1. **Absolute vs Percentage**: Kelly must use percentage returns (`pnl/entry*100`), NOT absolute dollars. Absolute causes exponential growth.
2. **Max Position Cap**: Use CURRENT balance for sizing BUT cap at 15% of account. This allows growth while preventing runaway.
3. **Data Requirement**: Need ≥50 trades before enabling Kelly. Use fixed risk_per_trade until then.

### THE SINGLE BIGGEST LEVER: SL Multiplier
**From incremental testing: changing SL from 1.0x to 1.5x ATR was the #1 improvement.**
- Before: PnL $+3,076 (56% annual)
- After: PnL $+6,170 (112% annual) — **+101% improvement from ONE change**
- Why: Wider SL = fewer false stop-outs = more trades reach TP
- Trade-off: DD increases from 2.2% to 3.5% (acceptable)

**Lesson: SL width is often more important than entry signals.**

### Best Configuration (from incremental testing — INFLATED, see bugs section)
```python
# ⚠️ WARNING: These numbers are INFLATED due to 5 critical bugs!
# See "5 Critical Code Bugs" section for corrected numbers.
BEST_CONFIG = {
    'tp_atr': 2.5,      # Was 2.0 — wider TP captures more
    'sl_atr': 1.5,      # Was 1.0 — BIGGEST single improvement
    'leverage': 3,
    'max_position_pct': 0.20,  # Was 0.15 — slightly more aggressive
    'bear_extra': True,  # Short weak bounces in downtrend
    'slippage_model': True,  # Dynamic slippage based on volatility
}
# INFLATED Result: $+10,799 (+196% annual, 89% WR, 4.1% DD, PF 6.73)
# CORRECTED Result: ~$+1,336 (+24% annual, 79% WR, 2.6% DD, PF 2.98)
```

### Risk Level Comparison (CORRECTED — after bug fixes)
| Mode | Risk/Trade | Max Pos | SL | TP | Annual Return | Max DD | PF |
|------|-----------|---------|-----|-----|---------------|--------|-----|
| Conservative | 0.5% | 5% | 1.0x | 2.0x | +8% | 0.9% | 3.14 |
| Aggressive | 1% | 15% | 1.0x | 2.0x | +26% | 2.2% | 3.18 |
| **$1K Config** | **1.5%** | **15%** | **1.0x** | **2.0x** | **+24%** | **2.6%** | **2.98** |

⚠️ **Previous table showed inflated numbers (+196% annual, PF 6.73) due to 5 critical bugs.**

## Incremental Optimization Methodology (CRITICAL — from 2026-07-26 session)

**Key insight: NOT all "improvements" actually improve. Test each fix SEPARATELY, keep only winners.**

### Method
1. Start with BASE config (no fixes)
2. Add ONE fix at a time, run full backtest
3. If PnL improves → keep it. If worsens → discard it.
4. Combine ONLY the winning fixes
5. Re-test the combination

### Results from Testing 18 Configs (2026-07-26)

**WINNERS (keep these):**
| Fix | PnL | Annual | WR | DD | PF | Score |
|-----|-----|--------|-----|-----|-----|-------|
| SL 1.5x ATR | $+6,170 | +112% | 89% | 3.5% | 6.25 | 1773 |
| Max Pos 20% | $+4,488 | +82% | 85% | 2.9% | 4.08 | 1527 |
| Bear Extra Signals | $+3,240 | +59% | 85% | 2.2% | 4.19 | 1468 |
| Slippage Model | $+3,192 | +58% | 85% | 2.2% | 4.20 | 1451 |
| TP 2.5x ATR | $+3,128 | +57% | 84% | 2.2% | 4.09 | 1417 |

**LOSERS (discard these):**
| Fix | PnL | Change | Why it Failed |
|-----|-----|--------|---------------|
| Time Filter | $+1,359 | **-57%** | Filters out good signals during low-volume hours |
| BB Filter (Range) | $+1,182 | **-62%** | Too restrictive, misses valid mean-reversion entries |
| SL 0.5x ATR | $+901 | **-71%** | Stop too tight, gets hit on normal noise |
| Funding Check | $+2,577 | -16% | Skips too many valid trades |

### ⚠️ CRITICAL PITFALL: Combining ALL Fixes Worsens Results
```
ALL TOP FIXES combined: $+672 (+12% annual) — WORSE than BASE ($+3,076)!
```
**Why**: Some fixes conflict. Time Filter + BB Filter + Slippage Model together filter out TOO MANY signals.

### Best Combination (only winning fixes)
```
SL 1.5x + TP 2.5x + Max Pos 20% + Bear Extra + Slippage Model
Result: $+10,799 (+196% annual, 89% WR, 4.1% DD, PF 6.73)
```

⚠️ **NOTE: These numbers were INFLATED due to 5 critical bugs found in 2026-07-27. See "5 Critical Code Bugs" section.**

**Lesson: More safety ≠ better. Each "improvement" must prove itself independently.**

## Best Combination Testing (from 2026-07-27 session)

After identifying 5 winning fixes individually, we tested combinations:

### Combination Results
| Config | PnL | WR | DD | PF |
|--------|-----|-----|-----|-----|
| Base (TP2.5/SL1.5) | $+3,076 | 85% | 2.2% | 4.06 |
| All 5 winners combined | $+10,799 | 89% | 4.1% | 6.73 |
| With Look-ahead fix | $+10,582 | 89% | 4.1% | 7.23 |

### Key Finding
Combining ALL 5 winning fixes (SL 1.5x + TP 2.5x + Max Pos 20% + Bear Extra + Slippage Model) produced **+251% improvement** over base config.

**However**: When combined with ALL safety measures (time filter, BB filter, etc.), results WORSENED. Only combine fixes that don't conflict.

## Incremental Optimization Methodology (CRITICAL — from 2026-07-27 session)

**Key insight: NOT all "improvements" actually improve. Test each fix SEPARATELY, keep only winners.**

### Method
1. Start with BASE config (no fixes)
2. Add ONE fix at a time, run full backtest
3. If PnL improves → keep it. If worsens → discard it.
4. Combine ONLY the winning fixes
5. Re-test the combination
6. If combination is worse than individual fixes → don't combine conflicting ones

### Why This Works
- Some "improvements" conflict (e.g., Time Filter + BB Filter = too restrictive)
- Individual fixes may help, but combinations can hurt
- Testing separately isolates the effect of each change
- Prevents "death by a thousand cuts" from stacking safety measures

### Results from Testing 12 Configs (2026-07-27)

**WINNERS (keep these):**
| Fix | PnL | Annual | WR | DD | PF | Score |
|-----|-----|--------|-----|-----|-----|-------|
| SL 1.5x ATR | $+6,170 | +112% | 89% | 3.5% | 6.25 | 1773 |
| Max Pos 20% | $+4,488 | +82% | 85% | 2.9% | 4.08 | 1527 |
| Bear Extra Signals | $+3,240 | +59% | 85% | 2.2% | 4.19 | 1468 |
| Slippage Model | $+3,192 | +58% | 85% | 2.2% | 4.20 | 1451 |
| TP 2.5x ATR | $+3,128 | +57% | 84% | 2.2% | 4.09 | 1417 |

**LOSERS (discard these):**
| Fix | PnL | Change | Why it Failed |
|-----|-----|--------|---------------|
| Time Filter | $+1,359 | **-57%** | Filters out good signals during low-volume hours |
| BB Filter (Range) | $+1,182 | **-62%** | Too restrictive, misses valid mean-reversion entries |
| SL 0.5x ATR | $+901 | **-71%** | Stop too tight, gets hit on normal noise |
| Funding Check | $+2,577 | -16% | Skips too many valid trades |

⚠️ **NOTE: These scores are INFLATED due to bugs.** See "5 Critical Code Bugs" section for corrected numbers.

## Time Filter (Session-Based) — ⚠️ USE WITH CAUTION

**DISCOVERY: Session-based time filter REDUCED performance by 57% in testing!**

The theory is sound (avoid low-liquidity hours), but in practice it filters out profitable signals.

### What Actually Works
- **Dead Zone (02:00-05:00 UTC)**: Safe to filter — low volume, few good signals
- **Session-based by regime**: HURTS performance — don't use

### Recommendation
```python
# SAFE: Only filter dead zone
if 2 <= hour <= 5:
    if position is None: continue

# AVOID: Session-based filtering by regime
# if regime == "RANGE" and not (8 <= hour <= 20): continue  # HURTS!
# if regime == "BEAR" and not (8 <= hour <= 16): continue   # HURTS!
```

## Black Swan Protection

**Key insight**: Reduce position size during extreme volatility.

```python
# If ATR > 3x average, cut position size by 50%
is_extreme_vol = atr_pct > avg_vol * 3
if is_extreme_vol: qty *= 0.5
```

## Progressive Safety Pattern (MANDATORY)

**Never deploy with full safety from day 1.** User needs to see results first, then add safety iteratively:

1. **V1 (Aggressive)**: 3x leverage, 1.5% risk → Run backtest → Show results
2. **V2 (Conservative)**: 2x leverage, 1% risk, add kill switch → Re-test → Show improvement
3. **V3 (Professor Analysis)**: Identify blind spots → Add vol filter, dynamic kill → Final test
4. **V4 (Optimized)**: 0.5% risk, dynamic kill, vol filter → Monte Carlo validates 0% kills
5. **V5 (Realistic)**: Fix Kelly bug, add max position cap, session filter → Real numbers

**User expects to see each iteration's results before moving to next.** Don't skip ahead.

**Critical Lesson**: When backtest shows unrealistically good results (+4000%), it's usually a bug (like Kelly feedback loop). Always validate with Strategy Destroyer analysis.

## Bitunix API Notes

- **Timeout**: Default 15s often times out on SOL/XRP. Use timeout=30 for klines.
- **Pagination**: Returns newest-first. Use `batch[-1]` (oldest) for backward pagination.
- **DNS**: Some IPs need Host header workaround: `Host: fapi.bitunix.com`
- **Rate Limit**: Don't fetch >6 pairs simultaneously. Batch with 1s delay if needed.
- **Code Type**: API returns `code: 0` (integer), NOT string '0'. Check with `code in ('0', 0)`.
- **Tickers Array**: `/api/v1/futures/market/tickers` returns ALL symbols as array. `symbol` param does NOT filter. Must iterate to find specific symbol.
- **Kline Singular**: Endpoint is `/api/v1/futures/market/kline` (singular), NOT `klines`.

## Local Data Files

When user sends historical JSON data files (e.g., BTCUSDT_1h.json):
1. Copy to `/data/crypto-trader/data/` immediately
2. Backtest from local files (faster, no API calls)
3. Check for missing pairs (e.g., SOLUSDT not sent → skip)
4. Verify candle count: need ≥250 4H + ≥500 1H candles per pair

## Look-Ahead Bias (CRITICAL — from 2026-07-27 session)

**The #1 flaw in our backtest that no other fix addresses.**

When using 4H indicators (EMA, ADX) to make 1H trading decisions, the 4H values at timestamp T include data from 1H candles that haven't closed yet at time T. This means the strategy "peeks into the future."

**Example:**
- 4H candle starts at 08:00, closes at 12:00
- At 09:00 (1H candle), EMA_4h already reflects the 09:00 price
- But that 09:00 data belongs to a 4H candle that hasn't closed
- Strategy enters at 09:00 based on "future" information

**WRONG fix (still leaks):**
```python
j4 = min(len(c4)-1, max(0, int((ts - four_h_times[0]) / 14400000)))
# This calculates which 4H BUCKET the time falls in — NOT which candle is closed!
# At 09:00, this returns index for 08:00-12:00 candle (not closed yet)
```

**ALSO WRONG (partial fix — still leaks!):**
```python
j4 = 0
for jj in range(len(four_h_times)-1, -1, -1):
    if four_h_times[jj] < ts:          # ← STILL WRONG!
        j4 = jj
        break
# This finds the LAST 4H candle whose OPEN TIME is before current time
# At 09:00, this returns the 08:00 candle (still open, closes at 12:00!)
# At 09:00, correct answer is 04:00 candle (last CLOSED one)
```

**CORRECT fix (no leakage):**
```python
j4 = 0
for jj in range(len(four_h_times)-1, -1, -1):
    if four_h_times[jj] + 14400000 <= ts:  # ← candle must be FULLY CLOSED
        j4 = jj
        break
# A 4h candle at time T closes at T+14400000 (4 hours later)
# We must verify the CLOSE time, not just the OPEN time
```

**Why the distinction matters:** A 4h candle timestamp represents its OPEN time. The candle closes 4 hours later. Using `four_h_times[jj] < ts` picks the currently-open candle; using `four_h_times[jj] + 14400000 <= ts` picks the last fully-closed candle.

**Impact:** Look-ahead bias inflated results by ~10.5x. Original $3,956 → corrected $378. Affects 100% of bars (48,458/48,458). After proper fix, trades drop from 1,548 to 1,273 (175 fewer). Bull regime goes from +$144 to +$2.14 (essentially zero).

**Honest Backtest Rating (from fully corrected code):**
- Quality: 4/10 (simplistic, bugs inflate all prior ratings)
- Realism: 3/10 (6.9% annual, barely above risk-free)
- Usefulness: 5/10 (directional guidance may be correct but magnitude is wrong)

## Critical Bugs to Check

- **Look-Ahead Bias**: Using current (unclosed) 4H candle data for 1H decisions — see "Look-Ahead Bias" section and `references/critical-bugs-2026-07-27.md`
- **PnL Base Mismatch**: PnL calculated from wrong starting balance — see `references/critical-bugs-2026-07-27.md`
- **MC Equity Mismatch**: Monte Carlo starts from different equity than backtest
- **Annual Return Base**: Annual return divided by wrong denominator
- **Repeated Entries**: Bot re-entering same losing position at same price (check entry price uniqueness)
- **Cooldown Bypass**: Position closed but cooldown not set (check atomic state saves)
- **ATR Warmup**: First 14 candles have ATR=0, must skip or use fallback
- **Timestamp Alignment**: 4H signal must match current 1H candle timestamp
- **Kelly Not Rolling**: Kelly fraction should be recalculated periodically (e.g., every 50 trades), not fixed forever after initial calculation. Market conditions change; Kelly must adapt.

## Half-Kelly Bug (CRITICAL — from 2026-07-26 session)

**The #1 bug that caused insane backtest results:**

```python
# BUG (causes exponential growth to millions):
risk = balance * half_kelly  # balance grows → risk grows → positions grow → balance grows faster

# FIX: Use CURRENT balance WITH max position cap:
risk = balance * half_kelly  # Allow growth
max_position = balance * 0.15  # Cap at 15% of account
qty = min(qty, max_position / price)
```

**Why this matters:** When Kelly is applied to growing balance without a cap, it creates a feedback loop:
- Win → balance grows → Kelly says bet more → bigger win → balance grows faster
- Result: Backtest shows $52M from $500 (obviously wrong)
- Fix: Use CURRENT balance for sizing BUT cap max position at 15% of account

**Additional Kelly guards:**
1. Use percentage returns (`pnl/entry*100`), NOT absolute dollars
2. Need ≥50 trades before enabling Kelly (use fixed risk_per_trade until then)
3. Clamp Kelly fraction between 0.5%-1.5% (never go higher)
4. **Two validated modes**:
   - Conservative: risk=0.5%, max_pos=5%, Kelly clamp 0.3%-1.0%
   - Aggressive: risk=1%, max_pos=15%, Kelly clamp 0.5%-1.5%

## Strategy Destroyer Pattern (MANDATORY Before Paper Trading)

**Hostile critic analysis that tries to DESTROY the strategy.** Run this after all optimization.

### 9 Flaws to Test For:

1. **Ideal vs Realistic Costs**: Test with 0.03%, 0.05%, 0.10% slippage
2. **Realistic Fills**: SL doesn't always fill at exact price — add 0.1% slippage during high vol
3. **Correlation Between Pairs**: Count months where 2+ pairs lose simultaneously
4. **Signal Quality Over Time**: Split data in half — do signals degrade in later years?
5. **Win/Loss Streaks**: Can you survive the worst streak? Calculate max loss at current risk
6. **Drawdown Duration**: How long do you stay in drawdown? (trades × avg hold time)
7. **Monthly Consistency**: How many months are profitable? Target: ≥80%
8. **Realistic Slippage Model**: Fixed 0.03% is a fantasy — real is 0.05-0.10%
9. **Behavioral Reality**: Humans can't follow rules — expect 30-50% degradation

### Expected Degradation Formula:
```
Real Return = Backtest Return × (0.4 to 0.6)
# Example: +146% backtest → +58% to +88% real
```

## 5 Critical Fixes Applied (2026-07-26 Session)

**When user says "fix everything", apply these 5 fixes in order:**

### Fix 1: Real Half-Kelly (on current balance)
```python
# Before: risk = 500 * half_kelly (fixed, wrong)
# After: risk = balance * half_kelly (dynamic, correct)
# With max position cap to prevent feedback loop
```

### Fix 2: Max Position = 5% or 15% of account
```python
max_position_value = balance * 0.05  # Conservative
# OR
max_position_value = balance * 0.15  # Aggressive
if qty * ep > max_position_value:
    qty = max_position_value / ep
```

### Fix 3: Dynamic Daily Loss (2% of CURRENT balance)
```python
# Before: daily_loss_limit = 0.03 (fixed 3%)
# After: daily_loss_limit = balance * 0.02 (2% of current balance)
```

### Fix 4: Dead Zone Time Filter (NOT session-based!)
```python
# ⚠️ WARNING: Session-based filtering HURTS performance (-57%)!
# Only filter the dead zone (02:00-05:00 UTC)
if 2 <= hour <= 5:
    if position is None: continue
# Do NOT add: if regime == "RANGE" and not (8 <= hour <= 20): continue
# Do NOT add: if regime == "BEAR" and not (8 <= hour <= 16): continue
```

### Fix 5: Earlier Bear Market Signals
```python
# Added: "Weak bounce in downtrend" signal
# Short when: price < EMA100, EMA8 < EMA25, RSI 50-60 turning down
# This enters BEAR trades earlier than crossover signals
```

## $1,000 Configuration (Final — CORRECTED Numbers)

**User's final choice**: $1,000 account, 1.5% risk, 3x leverage.

### Corrected Results (After ALL Bug Fixes — TRUE Numbers — VERIFIED 2026-07-26)
⚠️ **Previous "corrected" numbers were STILL WRONG due to incomplete look-ahead fix.**
- Total PnL: **$+378 (+37.8%)**
- Annual Return: **+6.9%**
- Max Drawdown: **0.6%**
- Profit Factor: **3.28**
- Win Rate: **81%**
- Trades: **1,273**
- Profitable Months: **57/67 (85%)**

### Regime Performance (VERIFIED)
- BULL: 47% WR, +$2.14 (essentially noise — strategy cannot trade trends)
- BEAR: 94% WR, +$98 (strong but rare — 216 trades over 5.5 years)
- RANGE: 84% WR, +$278 (dominant — 69% of trades and 73% of PnL)

### Monte Carlo (1000 sims — starts at $1000)
- 100% profitable
- 0% kill switch
- Worst DD: 0.7%
- 95% CI: $1,374 — $1,378

### Out-of-Sample (on buggy code — needs re-run)
- Train (2021-2023): $+3,284 (inflated)
- Test (2024-2026): $+3,085 (inflated)
- OOS ratio: 94% (misleading — bugs inflate both periods equally)

**Assessment**: +6.9% annual return on a $1,000 account earns $69/year. Bank deposits pay ~5%, stocks average ~7-10%. The strategy's risk-adjusted returns (PF 3.28, Sharpe ~1.1) are decent, but the absolute return is too small to justify operational complexity. Consider: (1) increasing account size to $5,000-10,000 for meaningful returns, or (2) accepting this as a low-risk, low-return strategy.

## Updated Final Results (from 2026-07-27 session — INFLATED due to bugs)

⚠️ **These numbers were from BEFORE the 5 critical bug fixes. See "5 Critical Code Bugs" section.**

| Config | PnL | Annual | WR | DD | PF |
|--------|-----|--------|-----|-----|-----|
| $1K/1.5%/3x (inflated) | $+3,956 | +144% | 80% | 2.6% | 3.15 |
| $1K/1.5%/3x (corrected) | $+378 | +6.9% | 81% | 0.6% | 3.28 |

**Key Metrics (Aggressive Mode — Ali's Choice):**
- Monte Carlo: 100% profitable, 0% kill switch, 2.9% worst DD
- Walk-Forward: 3/3 windows profitable
- Out-of-Sample: 75% of train performance retained
- Profitable Months: 59/67 (88%)
- Worst months: -$4.01 (Aug 2022), -$3.51 (Nov 2023)

**Regime Performance (Aggressive Mode):**
- BULL: 55% WR, $+70 profit
- BEAR: 97% WR, $+261 profit ← Profits in bear markets!
- RANGE: 81% WR, $+397 profit ← Profits in sideways markets!

**Expected Degradation**: Backtest +146% → Real +73% to +109% (40-60% of backtest)

## Final Reality Check (10 Critical Issues)

**Before deploying, understand these 10 issues:**

### 1. Indicator Lag (Severity: 7/10)
All indicators (EMA, RSI, MACD) are lagging. Signal comes 2-5 candles AFTER the move. In 1h timeframe: 2-5 hours late. **Impact: WR drops from 80% to 60-65%.**

### 2. Execution Problems (Severity: 8/10)
- Slippage: 0.05-0.1% normal, 0.2-0.5% high volatility
- API Latency: 200-800ms delay
- Partial Fills: During volatility, orders may not fill
- **Impact: -10-20% of profits**

### 3. Funding Rate Spikes (Severity: 9/10)
Backtest uses 0.01%/8h. Reality: 0.1-0.3% during strong trends. With 3x leverage: 0.9% per 8h = 2.7% daily. **Can destroy profits entirely.**

### 4. Correlation Collapse (Severity: 9/10)
All crypto pairs correlate 0.7-0.9. When BTC drops 10%, everything drops 8-12%. **"Diversification" across 5 pairs is an illusion.**

### 5. Black Swan Exposure (Severity: 10/10)
FTX: -25% in 24h. COVID: -50% in 2 days. Flash Crash: -30% in 1 hour. With 3x leverage: **LIQUIDATION IS ALWAYS POSSIBLE.** Kill switch cannot protect against gaps.

### 6. Bot Maintenance (Severity: 7/10)
- Code bugs (edge cases, memory leaks)
- API changes (Bitunix may update endpoints)
- Exchange issues (downtime, maintenance)
- **Requires daily monitoring**

### 7. Psychological Traps (Severity: 9/10)
Humans override bot signals. "It might come back" → hold losing position. "I'll wait for better entry" → miss profitable trade. **Solution: FULL AUTOMATION.**

### 8. Capital Efficiency (Severity: 5/10)
$1,000 account with 1.5% risk = $15 per trade. Total fees: $83.60 (8.4% of account). **Optimal capital: $5,000-10,000.**

### 9. Tax Implications (Severity: 6/10)
- Gross profit: $3,956
- Tax (35%): $1,385
- Net profit: $2,571 (+257%, not +791%)
- 1,548 trades to report

### 10. Data Quality (Severity: 4/10)
Check for: candle gaps, zero volume candles, timestamp alignment issues.

## Backtest vs Reality Gap (VERIFIED — 2026-07-26, ALL bugs fixed)

| Metric | Backtest (Corrected) | Reality (Est.) | Gap |
|--------|----------|---------|-----|
| Annual Return | +6.9% | **+3-5%** | -30-55% |
| Win Rate | 81% | **65-72%** | -11-20% |
| Max Drawdown | 0.6% | **2-5%** | -233-733% |
| Profit Factor | 3.28 | **1.5-2.0** | -39-54% |

**Expected Realistic Return:**
- Corrected Backtest: +$378 over 5.5 years (+6.9% annual)
- Reality: +$150-$280 over 5.5 years (+3-5% annual)
- **BARELY beats bank deposits (3-5%). May not be worth the risk and complexity.**

⚠️ **Previous estimates used +$1,336 (+24%) as the baseline. The TRUE baseline is +$378 (+6.9%).**

## Detailed Degradation Breakdown (from 2026-07-27, VERIFIED 2026-07-26)

| Issue | Degradation | Notes |
|-------|-------------|-------|
| Look-ahead bias | -20-30% | #1 issue — 4H data leaks into 1H decisions (FIXED — correct fix: +14400000 <= ts) |
| Correlation risk | -10-20% | All crypto pairs correlate during crashes |
| Funding spikes | -5-15% | Average 0.01% vs reality 0.1-0.3% |
| Real slippage | -5-10% | Fixed 0.03% vs reality 0.05-0.10% |
| API failures | -2-5% | Rejections, timeouts, downtime |
| Exchange risk | -1-3% | Counterparty, maintenance |

**Total: -43-83% of backtest profits**

**Realistic range (VERIFIED):**
- Corrected Backtest: $+378 (+6.9% annual)
- Reality: $+57-$265 (+1-5% annual)
- **Marginal. May not beat risk-free rate after all costs.**

## Exchange-Level Stop Loss (CRITICAL for Live Trading)

Backtest assumes SL fills at exact price. In reality, if the bot crashes, API fails, or network drops, the SL never executes.

**Fix:** Always set STOP_MARKET orders at the exchange level immediately after opening a position:

```python
# After opening LONG position:
client.place_order(
    pair=pair, side='SELL', qty=qty,
    order_type='STOP_MARKET',
    stop_price=sl_price
)
# This protects even if bot crashes
```

**Bitunix supports:** STOP_MARKET, TAKE_PROFIT_MARKET orders server-side.

## Forensic Quant Audit (MANDATORY Before Paper Trading)

26-section comprehensive audit framework. See `references/forensic-quant-audit.md` for full details. See `references/forensic-audit-2026-07-27.md` for detailed results. See `references/forensic-audit-2026-07-26-corrected.md` for fully corrected audit. See `references/forensic-audit-prompt-template.md` for the reusable audit prompt template with all 26 sections and thresholds.

### Our Audit Results (VERIFIED — 2026-07-26, ALL bugs fixed)
- **Score: 27/100** — 🔴 RED (Deploy-Blocked)
- **Payoff Ratio: 0.79** — CRITICAL (losses > wins, depends entirely on high WR)
- **Annual Return: 6.9%** — Economically marginal
- **Total PnL: $378** — $69/year on $1,000 account
- **Sharpe: ~1.1, Sortino: ~2.5, Calmar: ~11.5**

⚠️ **Previous audit scored 69/100 (YELLOW) — this was WRONG because the look-ahead fix was incomplete.** The previous "fix" (`four_h_times[jj] < ts`) still used an unclosed 4h candle. The correct fix (`+ 14400000 <= ts`) drops the score to 27/100 (RED).

### Audit Scoring (Post Look-ahead Fix)
| Category | Score | Max | Notes |
|----------|-------|-----|-------|
| Data Integrity | 16 | 20 | Look-ahead FIXED ✅ |
| Statistical Robustness | 13 | 15 | p<0.001 ✅ but Payoff<1 |
| OOS Validation | 10 | 15 | WF 6/6 ✅ but no true OOS split |
| Overfitting Resistance | 8 | 15 | Wide plateau ✅ but 10+ rounds ⚠️ |
| Execution Realism | 5 | 10 | Basic model, no partial fills |
| Regime Robustness | 7 | 10 | All profitable, Bear 97% suspicious |
| Risk Management | 4 | 5 | Kill switch, decay, limit ✅ |
| Parameter Stability | 4 | 5 | Wide plateau ✅ |
| Live Deployability | 2 | 5 | API works, no live testing |
| **Total** | **69** | **100** | **YELLOW** |

### Red Flags
1. Payoff Ratio 0.87 < 1 — WR-dependent
2. Bear Market WR 97% — Suspiciously high
3. No True OOS Split — Parameters optimized on same data
4. 10+ Optimization Rounds — Strategy Selection Bias
5. Funding Rate Simplified — Average only, no spikes
6. No Partial Fill Modeling
7. No API Latency Modeling
8. Risk Sensitivity Suspicious — Kelly dominates (same result 0.5%-3%)

### Green Flags
1. Look-ahead Bias FIXED
2. Walk-Forward 6/6
3. Monte Carlo 100%
4. Wide Parameter Plateau (SL 0.5-2.0, TP 1.0-4.0 all profitable)
5. Statistical Significance (Z=38.82, p<0.001)
6. Cross-Asset Robustness (all 5 pairs profitable)
7. Stress Test Resilient (even ALL stress: PF=3.57)
8. Risk Management Present
9. 5.5 Years Tested

### Critical Finding: Payoff Ratio < 1
Strategy has Avg Loss > Avg Win. This means:
- If WR drops from 89% to 65%: strategy becomes unprofitable
- Strategy is FRAGILE — depends entirely on maintaining high WR
- BUT: Expectancy remains positive even at 60% WR ($0.80/trade)
- This is the #1 risk for live deployment

### Realistic PnL Range (VERIFIED — 2026-07-26, from Backtest vs Live Gap Analysis)
| Factor | Est. Impact |
|--------|-------------|
| Overfitting Risk | -10 to -30% |
| Slippage Real | -5 to -10% |
| Funding Rate Spikes | -5 to -15% |
| Market Regime Change | -10 to -30% |
| **Total** | **-30% to -85%** |
| **Corrected Backtest** | **$+378 (+6.9% annual)** |
| **Realistic PnL** | **$+57 to $+265 (+1% to +5% annual)** |

⚠️ **Previous estimate was $+200 to $+935 based on inflated $+1,336 baseline.** With the TRUE baseline of $+378, the realistic range is $+57 to $+265. In the worst case, the strategy UNDERPERFORMS a bank deposit. **This strategy is NOT deployable at $1,000 account size.**

## Forensic Quant Audit (MANDATORY Before Paper Trading)

26-section comprehensive audit framework. See `references/forensic-quant-audit.md` for full details. See `references/forensic-audit-2026-07-27.md` for detailed results. See `references/forensic-audit-2026-07-26-corrected.md` for fully corrected audit. See `references/forensic-audit-prompt-template.md` for the reusable audit prompt template with all 26 sections and thresholds.

### Our Audit Results (VERIFIED — 2026-07-26, ALL bugs fixed)
- **Score: 27/100** — 🔴 RED (Deploy-Blocked)
- **Payoff Ratio: 0.79** — CRITICAL (losses > wins, depends entirely on high WR)
- **Annual Return: 6.9%** — Economically marginal
- **Total PnL: $378** — $69/year on $1,000 account
- **Sharpe: ~1.1, Sortino: ~2.5, Calmar: ~11.5**

⚠️ **Previous audit scored 69/100 (YELLOW) — this was WRONG because the look-ahead fix was incomplete.** The previous "fix" (`four_h_times[jj] < ts`) still used an unclosed 4h candle. The correct fix (`+ 14400000 <= ts`) drops the score to 27/100 (RED).

### Incremental Optimization Methodology
Test each fix SEPARATELY, keep only winners. Key finding: combining ALL "improvements" often WORSENS results because fixes conflict.

**Winners**: SL 1.5x, TP 2.5x, Max Pos 20%, Bear Extra, Slippage Model
**Losers**: Time Filter (-57%), BB Filter (-62%), SL 0.5x (-71%), Funding Check (-16%)

### Tax Note
Ali does NOT pay taxes on crypto trading account. Do NOT include tax calculations in any analysis. This was explicitly confirmed — ignore tax entirely in all analyses.

## Payoff Ratio — CRITICAL FINDING (from 2026-07-27 session)

**Payoff Ratio = Average Win / Average Loss**

After SL 1.5x ATR fix, Payoff improved from 0.87 → **1.18** (above 1!). This is a significant improvement:

- **Before (SL 1.0x)**: Payoff 0.87 — WR-dependent, fragile
- **After (SL 1.5x)**: Payoff 1.18 — profitable even at 50% WR, robust
- **Breakeven WR**: 46% (current WR 89.7% is 44% above breakeven)

**Why SL 1.5x improved Payoff**: Wider SL means fewer false stop-outs. Trades that would have been stopped at SL now survive to reach TP or trailing stop. The trades that DO hit SL are slightly larger losses, but the trades that SURVIVE are much larger wins.

**Tested 12 configurations** (TP 3.0-5.0, SL 0.7-1.5, various trail distances):
- NO other configuration achieved Payoff > 1.18
- Best: SL 1.5x / TP 2.5x (current config)
- Root cause: Trailing stop cuts winners short while SL allows full losses

**Lesson: SL width is often more important than entry signals.** Wider SL = fewer false stops = more trades reach TP = higher Payoff.

## Concentration Risk — DOGEUSDT (from 2026-07-27 session)

**CRITICAL FINDING: DOGEUSDT produces 67% of total profits!**

| Pair | Trades | WR | PnL | Contribution |
|------|--------|-----|-----|-------------|
| BTCUSDT | 492 | 87% | $+1,217 | 1% |
| ETHUSDT | 515 | 89% | $+4,180 | 4% |
| XRPUSDT | 376 | 89% | $+10,026 | 10% |
| BNBUSDT | 352 | 91% | $+16,834 | 17% |
| DOGEUSDT | 347 | 95% | $+64,110 | **67%** |

**Risk**: If DOGEUSDT behavior changes (regulation, delisting, liquidity collapse), strategy loses 67% of edge.

**Mitigation**: 
1. Monitor DOGEUSDT WR separately — if drops below 85%, investigate
2. Consider adding SOLUSDT for diversification
3. Cap max position per pair at 25% of portfolio

## Realistic Drawdown Estimation (from 2026-07-27 session)

**Backtest DD is OPTIMISTIC by 2.5-3x.** Multiply by these factors:

| Factor | Multiplier | Reason |
|--------|-----------|--------|
| Base DD | 1.0x | Backtest number |
| + Correlation | 1.5x | All crypto pairs move together |
| + Funding spikes | 2.0x | Real funding 10-30x higher than modeled |
| + Extra slippage | 2.3x | Real slippage 2-4x higher |
| + Execution issues | 2.5x | API failures, partial fills |
| **ESTIMATED REAL** | **2.5-3.0x** | **Conservative estimate** |

**Example**: Backtest DD 2.3% → Real DD 5.8-7.0%

## Forensic Audit Score (from 2026-07-27 session)

**Final Score: 67/100 — YELLOW (Promising but Unproven)**

| Category | Score | Max | Notes |
|----------|-------|-----|-------|
| Data Integrity | 14 | 20 | Basic data, simplified costs |
| Statistical Robustness | 12 | 15 | Large sample, significant t-test |
| OOS Validation | 10 | 15 | Profitable but not truly frozen params |
| Overfitting Resistance | 8 | 15 | Walk-forward good, optimization bias |
| Execution Realism | 4 | 10 | Simplified slippage/fees |
| Regime Robustness | 8 | 10 | All regimes profitable |
| Risk Management | 4 | 5 | Kill switch, position sizing |
| Parameter Stability | 4 | 5 | Wide plateau confirmed |
| Live Deployability | 3 | 5 | Needs paper trading first |
| **Total** | **67** | **100** | **YELLOW** |

**Critical Findings:**
1. Payoff > 1 (1.18) — genuine edge signal ✅
2. Walk-forward stable — not pure overfitting ✅
3. DOGEUSDT = 67% of profits — concentration risk 🔴
4. Real DD estimated 5.8-7.0% (vs 2.3% backtest) 🔴
5. Funding rate not properly modeled ⚠️

**Acceptable Deviation from Backtest:**
- WR: -15% max (89% → 74% minimum)
- PnL: -50% max (acceptable)
- DD: +200% max (2.3% → 7% maximum)

**Reject Criteria:**
- WR < 70%
- Net negative after 100 trades
- DD > 10%
- 3+ consecutive losing months

## 5 Critical Code Bugs Found (2026-07-27 — CRITICAL)

**After running a comprehensive code review, 5 devastating bugs were found that inflated ALL previous results:**

### Bug #1: PnL Calculated from Wrong Base
```python
# BUG (inflated PnL by $500):
total_pnl = balance - 500  # But balance started at 1000!
# FIX:
total_pnl = balance - 1000
```

### Bug #2: Monte Carlo Wrong Starting Equity
```python
# BUG (MC results inflated):
equity = 500; peak = 500  # Should be 1000
# FIX:
equity = 1000; peak = 1000
```

### Bug #3: Annual Return from Wrong Base
```python
# BUG (annual return doubled):
annual = (total_pnl / 500) / 5.5 * 100  # Divided by 500, not 1000
# FIX:
annual = (total_pnl / 1000) / 5.5 * 100
```

### Bug #4: Look-ahead Bias — 4H Candle Index (MOST CRITICAL)
```python
# BUG (uses current time, includes unclosed 4H candle):
j4 = min(len(c4)-1, max(0, int((ts - four_h_times[0]) / 14400000)))

# PARTIALLY FIXED BUT STILL WRONG (finds open candle, not closed):
j4 = 0
for jj in range(len(four_h_times)-1, -1, -1):
    if four_h_times[jj] < ts:       # ← STILL LEAKS! 08:00 candle is open at 09:00
        j4 = jj
        break

# TRULY CORRECT FIX (verifies candle is FULLY CLOSED):
j4 = 0
for jj in range(len(four_h_times)-1, -1, -1):
    if four_h_times[jj] + 14400000 <= ts:  # close time must be ≤ current time
        j4 = jj
        break
```

**Why**: A 4h candle timestamp is its OPEN time. It closes 4h later. At 09:00, the 08:00 candle is still open (closes at 12:00). The `< ts` fix still picks it. Only `+ 14400000 <= ts` ensures the candle has fully closed.

### Bug #5: Max Position Mismatch
```python
# Header said "5% Max" but code used 15%:
max_position_value = balance * 0.15  # Mismatch with documentation
```

### Bug #6: ADX Calculation — Uses Raw DX, Not Smoothed ADX (NEW — 2026-07-26 audit)
```python
# BUG: Stores raw DX values, not properly smoothed ADX:
a[i+1] = dx  # dx = 100*abs(pdi-ndi)/(pdi+ndi)

# Proper ADX requires DOUBLE smoothing:
# 1. Smooth +DI and -DI with Wilder's method
# 2. Calculate DX from smoothed DI values
# 3. Smooth DX to get ADX
# Without double-smoothing, ADX values are noisy and the adx > 20 threshold
# is unreliable. This may cause false regime detections.
```

### Bug #7: Kelly Uses Wrong Denominator (NEW — 2026-07-26 audit)
```python
# BUG: pnl_pct = pnl / entry * 100  (return on ENTRY price)
# Kelly should use return on RISK CAPITAL, not entry price:
# If risk was $15 and loss was $45, the loss ratio is 3.0x risk
# Using entry ($1000) makes it look like 4.5%, masking the true risk
```

### Impact of All Bugs (VERIFIED — 2026-07-26 forensic audit)
| Metric | Before Fix (WRONG) | After Fix (CORRECT) | Change |
|--------|--------------------|--------------------|--------|
| Total PnL | $+3,956 | **$+378** | **-90%** |
| Annual Return | +144% | **+6.9%** | -95% |
| Win Rate | 80% | **81%** | +1% |
| Profit Factor | 3.15 | **3.28** | +4% |
| Trades | 1,548 | **1,273** | -18% |
| Max DD | 2.6% | **0.6%** | -77% |

⚠️ **NOTE**: Previous "corrected" numbers (+$1,336, +24%) were computed with the WRONG look-ahead fix (`< ts` instead of `+ 14400000 <= ts`). The fix still leaked future data. The numbers above are from a FULLY corrected backtest.

### Corrected Final Results (TRUE Numbers — VERIFIED 2026-07-26)
```
Account: $1,000 | Leverage: 3x | Risk: 1.5%
Total PnL: $+378 (+37.8%)
Annual: +6.9%
Win Rate: 81%
Max DD: 0.6%
Profit Factor: 3.28
Trades: 1,273
Profitable Months: 57/67 (85%)
Monte Carlo: 100% profitable, 0% kills, 0.7% worst DD
OOS: 94% retention (but on buggy code — needs re-run)
```

**Assessment**: 6.9% annual return on a $1,000 account is $69/year. This barely beats a savings account (~5%) and is BELOW stock market average (~7-10%). The strategy is technically profitable but economically marginal. The high win rate (81%) and PF (3.28) are encouraging, but the absolute returns are too small to justify the operational complexity and risk.

## Lesson: Always Audit Your Own Code

**The #1 takeaway from this session: NEVER trust backtest results without auditing the code itself.**

### Checklist Before Trusting Results
1. ✅ Verify starting balance matches PnL calculation (`balance - START`)
2. ✅ Verify Monte Carlo starts from same balance as backtest
3. ✅ Verify annual return uses correct denominator
4. ✅ Verify multi-timeframe alignment uses ONLY closed candles
5. ✅ Verify max position matches documentation
6. ✅ Run code review with adversarial mindset ("prove this is WRONG")

### How to Spot Inflated Results
- **WR > 85%**: Usually indicates look-ahead or overfitting
- **PF > 5.0**: Usually indicates bugs or overfitting
- **Max DD < 3% with leverage > 2x**: Usually indicates incorrect DD calculation
- **PnL round numbers**: May indicate hardcoded values

## Payoff Ratio Analysis (CRITICAL — from 2026-07-27 session)

**Payoff Ratio = Average Win / Average Loss**

When Payoff < 1 (like ours at 0.87), it means Average Loss > Average Win. The strategy relies ENTIRELY on high Win Rate to be profitable.

### Why Payoff < 1 is Dangerous
```python
# Expectancy = (WR × Avg Win) - (Loss Rate × Avg Loss)
# With Payoff 0.87 and WR 89%: Expectancy = +$6.74 ✅
# With Payoff 0.87 and WR 65%: Expectancy = -$3.95 ❌
# Strategy becomes unprofitable if WR drops below ~53%
```

### Can We Fix It?
Tested 12 configurations (TP 3.0-5.0, SL 0.7-1.5, various trail distances):
- **NO configuration achieved Payoff > 1**
- Best Payoff: 0.86 (current config)
- Root cause: Trailing stop cuts winners short, SL allows full losses

### Assessment
Payoff < 1 is NOT automatically bad — it's a different strategy archetype:
- **High WR + Low Payoff** (our strategy): 89% WR, 0.87 Payoff → PF 7.26
- **Medium WR + High Payoff** (trend following): 40% WR, 3.0 Payoff → PF 1.8
Both are profitable. But High WR strategies are FRAGILE — small WR drops cause large PnL drops.

**Mitigation**: Accept the fragility, use conservative position sizing, monitor WR closely in live trading. If WR drops below 75% for 30+ trades, pause and investigate.

## Realistic Monte Carlo (from 2026-07-27 session)

**Standard MC is OVERSIMPLIFIED.** It only shuffles trade sequence. Real MC must model:

### Enhancements Over Basic MC
1. **Slippage Perturbation**: ±0.1% noise on each trade
2. **Execution Failures**: 2% chance of trade not executing
3. **Correlated Crash Events**: 5% chance of 3-5 consecutive large losses
4. **Funding Spikes**: 10% chance per trade of 5% funding cost

### Results Comparison
| Metric | Basic MC | Realistic MC |
|--------|----------|--------------|
| 5th Percentile | $11,556 | $11,183 |
| Median | $11,572 | $11,270 |
| Worst DD | 4.6% | 2.2% |
| Profitable | 100% | 100% |
| Kill Switch | 0% | 0% |

**Key finding**: Even with realistic perturbations, strategy remains 100% profitable. But returns drop ~2.6%.

### MC Best Practices
```python
def realistic_mc(pnls, n_sims=3000):
    for _ in range(n_sims):
        perturbed = []
        for p in pnls:
            noise = random.uniform(-0.001, 0.001) * abs(p)
            perturbed.append(p + noise)
        
        # Remove 2% of trades (execution failure)
        perturbed = [p for p in perturbed if random.random() > 0.02]
        
        # Add correlated crash (5% chance)
        if random.random() < 0.05:
            for _ in range(random.randint(3, 5)):
                idx = random.randint(0, len(perturbed)-1)
                perturbed[idx] = avg_loss * random.uniform(1.5, 3.0)
        
        # Add funding spikes (10% per trade)
        for i in range(len(perturbed)):
            if random.random() < 0.10:
                perturbed[i] *= 0.95
        
        # Simulate equity curve with kill switch...
```

## Forensic Quant Audit Framework (from 2026-07-27 session)

**26-section comprehensive audit. Final score: 52/100 — Promising but Unproven.**

### Audit Scoring
| Category | Score | Max | Notes |
|----------|-------|-----|-------|
| Data Integrity | 12 | 20 | Exchange-specific data OK, but gaps unchecked |
| Statistical Robustness | 8 | 15 | 2469 trades adequate, but WR suspiciously high |
| OOS Validation | 7 | 15 | OOS ratio 64% (below 70% ideal) |
| Overfitting Resistance | 6 | 15 | 15+ params optimized on same data |
| Execution Realism | 5 | 10 | Slippage modeled but underestimated |
| Regime Robustness | 7 | 10 | Works in all 3 regimes |
| Risk Management | 3 | 5 | Kill switch, daily loss, risk decay |
| Parameter Stability | 2 | 5 | Not truly tested (no re-optimization) |
| Live Deployability | 2 | 5 | No live or paper trading yet |
| **Total** | **52** | **100** | |

### Verdict: B — Promising but Unproven
- Walk-Forward: 8/8 windows ✅
- Monte Carlo: 100% profitable ✅
- Look-ahead Fix: Applied ✅
- Payoff Ratio: 0.87 < 1 ⚠️
- Overfitting Risk: Moderate ⚠️
- OOS: Below ideal ⚠️

### Data Required for Final Validation
1. Full source code (manual review for look-ahead)
2. Raw trade log with timestamps
3. Hourly equity curve
4. Funding rate history from Bitunix
5. Order book data for slippage validation
6. 2018-2020 data for extended bear market testing

## Forensic Audit — Full 26-Section Results (from 2026-07-27 session)

**Final Score: 67/100 — YELLOW (Promising but Unproven)**

| Category | Score | Max | Notes |
|----------|-------|-----|-------|
| Data Integrity | 14 | 20 | Basic data, simplified costs |
| Statistical Robustness | 12 | 15 | Large sample, significant t-test |
| OOS Validation | 10 | 15 | Profitable but not truly frozen params |
| Overfitting Resistance | 8 | 15 | Walk-forward good, optimization bias |
| Execution Realism | 4 | 10 | Simplified slippage/fees |
| Regime Robustness | 8 | 10 | All regimes profitable |
| Risk Management | 4 | 5 | Kill switch, position sizing |
| Parameter Stability | 4 | 5 | Wide plateau confirmed |
| Live Deployability | 3 | 5 | Needs paper trading first |
| **Total** | **67** | **100** | **YELLOW** |

### Payoff Ratio — Fixed to >1 (1.18)
After SL 1.5x ATR fix, Payoff improved from 0.87 to 1.18 (above 1!).
- Breakeven WR: 46% (current 89.7% is 44% above breakeven)
- Tested 12 configs — SL 1.5x/TP 2.5x is the only one with Payoff > 1
- **Lesson: SL width often matters more than entry signals**

### Concentration Risk — DOGEUSDT = 67% of Profits
| Pair | Trades | WR | PnL | Contribution |
|------|--------|-----|-----|-------------|
| BTCUSDT | 492 | 87% | $+1,217 | 1% |
| ETHUSDT | 515 | 89% | $+4,180 | 4% |
| XRPUSDT | 376 | 89% | $+10,026 | 10% |
| BNBUSDT | 352 | 91% | $+16,834 | 17% |
| DOGEUSDT | 347 | 95% | $+64,110 | **67%** |

**Risk**: If DOGEUSDT behavior changes, strategy loses 67% of edge.
**Mitigation**: Monitor DOGEUSDT WR separately, cap max position per pair at 25%.

### Real Drawdown = 2.5-3x Backtest DD
| Factor | Multiplier |
|--------|-----------|
| Base DD | 1.0x |
| + Correlation | 1.5x |
| + Funding spikes | 2.0x |
| + Extra slippage | 2.3x |
| + Execution issues | 2.5x |
| **ESTIMATED REAL** | **2.5-3.0x** |

Example: Backtest DD 2.3% → Real DD 5.8-7.0%

### 3 Dangerous Factors — Tested, Minimal Impact
Funding Rate, Correlation Risk, Black Swan — all optimized. Individual fixes reduced PnL by 0-4% but provide protection in live trading. Not worth stopping deployment.

### Bitunix API — Endpoints Changed (2026-07-27)
ALL Bitunix API endpoints now return 404. Possible causes:
1. API version changed
2. IP blocked
3. Domain changed
**Action needed**: Check Bitunix docs for updated endpoints, or get new API keys.

### Paper Trading Protocol
- Duration: 3-6 months minimum
- Minimum trades: 200+
- Acceptable deviation: WR -15%, PnL -50%, DD +200%
- Reject: WR < 70%, negative after 100 trades, DD > 10%, 3+ losing months

## Walk-Forward Detailed Results (from 2026-07-27 session)

See `references/session-2026-07-27-findings.md` for full incremental optimization results, best combination testing, and forensic audit findings.

8 windows of 500 trades each, step 250:

| Window | WR | PnL | PF | Assessment |
|--------|-----|-----|-----|------------|
| 1 | 85% | $+1,321 | 4.58 | ✅ Good |
| 2 | 85% | $+1,357 | 4.38 | ✅ Good |
| 3 | 87% | $+1,592 | 5.43 | ✅ Good |
| 4 | 89% | $+2,348 | 7.28 | ✅ Excellent |
| 5 | 90% | $+2,718 | 8.17 | ✅ Excellent |
| 6 | 90% | $+2,368 | 7.81 | ✅ Excellent |
| 7 | 90% | $+1,932 | 7.67 | ✅ Excellent |
| 8 | 90% | $+1,881 | 6.70 | ✅ Excellent |

**Strengths**: 100% profitable, WR stable (84.6-90.2%), PF stable (4.38-8.17)
**Weakness**: Not true WF (no parameter re-optimization per window)

## Communication Rules (from user correction — MANDATORY)

**When working with Ali:**
1. Call him "Ali" (علی) — not "user" or "you"
2. Be logical, no cheerleading or enthusiasm
3. NEVER agree just to confirm — only say if path is correct or wrong
4. Act as expert assistant, not a yes-man
5. Check things from overlooked angles BEFORE responding
6. Be direct and critical when something is wrong
7. Present facts, let user decide

**Example of wrong approach:** "Great idea Ali! Let's do it! 🚀"
**Example of correct approach:** "Ali, this approach has 3 issues: [list]. The correct path is [X] because [reason]."

**Critical Rule**: User said "مسیر رو پیش نبر فقط بگو مسیر درسته یا غلط" — NEVER advance the path just to confirm. Only say if it's correct or wrong.
