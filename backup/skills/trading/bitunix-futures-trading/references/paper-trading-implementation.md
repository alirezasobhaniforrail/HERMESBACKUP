# Paper Trading Implementation - Complete Reference

## Overview
Full paper trading bot with complete order cycle simulation, risk management, and Telegram reporting.

## Architecture

### Core Components
1. **BitunixFutures API Client** - Authentication, klines, prices, account, positions
2. **Indicators** - EMA, RSI, ADX, MACD, ATR (pure Python, no dependencies)
3. **Strategy Engine** - Multi-regime (BULL/BEAR/RANGE) with ADX filter
4. **Position Manager** - Entry, TP/SL, monitoring, exit
5. **Risk Manager** - Half-Kelly sizing, max position, correlation limits
6. **State Persistence** - JSON files for equity, positions, trades, daily stats
7. **Telegram Reporter** - Real-time updates every cycle

## Strategy: V3.7 (Look-ahead Bias Fixed)

### Timeframes
- **4H**: Regime detection (EMA 8/25/100 stack, ADX ≥ 20)
- **1H**: Entry timing (RSI, MACD histogram, ATR for TP/SL)

### Regime Rules
| Regime | 4H Conditions | ADX |
|--------|---------------|-----|
| BULL | EMA8 > EMA25 > EMA100 | ≥ 20 |
| BEAR | EMA8 < EMA25 < EMA100 | ≥ 20 |
| RANGE | Otherwise | < 20 |

### Entry Rules
| Regime | Long | Short |
|--------|------|-------|
| BULL | EMA8>EMA25, RSI>45, MACD hist rising | — |
| BEAR | — | EMA8<EMA25, RSI<55, MACD hist falling |
| RANGE | RSI<30, MACD hist rising | RSI>70, MACD hist falling |

**Critical**: Only use CLOSED 4H candles (look-ahead bias fix).

### Exit Rules (ATR-Based)
- **TP**: Entry × (1 ± ATR_pct × 2.5)
- **SL**: Entry × (1 ∓ ATR_pct × 1.5)
- Ratio: 1.67:1 (TP:SL)

## Risk Management

### Position Sizing (Half-Kelly)
```
risk_amount = equity × 0.015 (1.5%)
sl_distance_pct = |entry - sl| / entry
position_value = risk_amount / sl_distance_pct
max_position = equity × 0.20 (20% cap)
final_value = min(position_value, max_position)
size = final_value / entry_price
```

### Limits
- Max 3 concurrent positions
- Max 2 same-direction (correlation)
- 3x leverage fixed
- Daily loss limit: -3%
- Kill switch: 20% DD

## Complete Order Cycle (Paper)

### 1. ENTRY
```python
signal = analyze_pair(api, symbol)  # Returns signal + TP/SL
success, pos = open_position(state, api, signal)
# Logs: symbol, side, entry, size, TP, SL, leverage, entry_time
```

### 2. TP/SL SET (Simulated)
```python
# In live: api.set_tpsl(symbol, tp, sl, size)
# Paper: store TP/SL in position dict
```

### 3. MONITOR (Every Hour)
```python
closed = check_tp_sl(state, api)
# Gets current price via klines endpoint
# Checks: LONG (price >= TP or price <= SL)
#         SHORT (price <= TP or price >= SL)
# Calculates PnL with leverage
```

### 4. EXIT
```python
trade = {
    'symbol', 'side', 'entry', 'exit', 'size', 'leverage',
    'pnl_pct', 'pnl_usd', 'exit_reason', 'entry_time', 
    'exit_time', 'duration_hours'
}
state['equity'] += pnl_usd
state['closed_trades'].append(trade)
log_trade(trade)
```

### 5. REPORT
Telegram message with:
- Account equity, daily PnL
- Open positions with unrealized PnL
- Market scan (all pairs, regime, indicators)
- Executed signals with TP/SL
- Stats (total trades, win rate, equity, return)

## Files

### Core Bot: `paper_trading_bot.py`
- BitunixFutures class (API)
- Indicators (EMA, RSI, ADX, MACD, ATR)
- analyze_pair() - strategy logic
- check_tp_sl() - exit monitoring
- open_position() - entry with sizing
- run() - main loop

### State Files
- `paper_state.json` - equity, positions, closed trades, daily PnL
- `paper_trades.json` - all trade logs (ENTRY + EXIT)
- `paper_daily.json` - daily summaries

### Cron Job
```bash
# Hourly
cd /data/crypto-trader && python3 paper_trading_bot.py
```

## Key Implementation Details

### Price Fetching (Fixed)
```python
def get_price(self, symbol):
    klines = self.get_klines(symbol, "1", 1)  # 1m klines
    if klines.get('data'):
        return float(klines['data'][0]['close'])
    return 0
```

### Indicators (Pure Python, No Dependencies)
- `calc_ema(data, period)` - Wilder's smoothing
- `calc_rsi(closes, period=14)` - Wilder's RSI
- `calc_adx(highs, lows, closes, period=14)` - Wilder's ADX
- `calc_macd(closes)` - EMA12 - EMA26, Signal EMA9
- `calc_atr(highs, lows, closes, period=14)` - Wilder's ATR

### State Management
```python
def load_state():
    # Ensures all keys exist with defaults
    # Handles migration from old formats

def save_state(state):
    # Atomic write with indent
```

### Telegram Formatting
```html
📄 <b>Paper Trading Bot</b>
⏰ 2026-07-28 15:45:48
==============================
🎯 <b>Positions Closed:</b>
  🔴 DOGEUSDT LONG SL: $-7.71 (-1.28%)
...
💰 <b>Paper Account:</b>
  Equity: $992.29
  Daily PnL: $-7.71
  Open Positions: 0/3
  Unrealized: $0.00
  Total Value: $992.29
...
📈 <b>Market Scan:</b>
  ⚪ BTCUSDT: $64,280.00 | RANGE | ADX:4 | RSI:37
...
✅ Telegram sent!
```

## Testing Results

### Force Test (10 Positions)
- 10 tests over ~20 minutes (2-min intervals)
- 10/10 passed (Entry → TP/SL → Monitor → Close)
- Win Rate: 50% (5 TP, 5 SL)
- Total PnL: +$30
- TP: $15 each | SL: -$9 each
- Ratio: 1.67:1 ✓

### Paper Trading Live (Since 2026-07-27)
- DOGEUSDT LONG: Entry $0.07231 → SL $0.07138 (-$7.71, -1.28%)
- Current Equity: $992.29
- All systems operational

## Deployment Checklist
- [ ] API keys in `bot_config_final.json`
- [ ] Telegram token/chat ID configured
- [ ] Cron job scheduled
- [ ] State files writable
- [ ] Logs directory exists