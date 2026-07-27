# Paper Trading Implementation (2026-07-27 Session)

## Complete Paper Trading Bot (`/data/crypto-trader/paper_trading_bot.py`)

### Features Implemented
1. **Position Management** - Open/close with TP/SL tracking
2. **Daily PnL Reset** - Date-based logic with automatic day rollover
3. **Correlation Limits** - Max 2 same-direction positions
4. **Risk-Based Position Sizing** - 1.5% risk per trade, 20% max per position, 3 max positions
5. **ATR-Based TP/SL** - 2.5x TP, 1.5x SL
5. **Full Trade Logging** - Entries, exits, PnL, duration
6. **Daily Summary Logging** - Equity, trades, win rate
7. **Telegram Hourly Reports** - Portfolio value, positions, signals, stats
8. **State Persistence** - JSON files (paper_state.json, paper_trades.json, paper_daily.json)

## Key Implementation Details

### Position Sizing (Half-Kelly)
```python
risk_amount = equity * 0.015  # 1.5%
sl_distance = abs(price - sl) / price
position_value = risk_amount / sl_distance
max_position_value = equity * 0.20
final_value = min(position_value, max_position_value)
size = max(final_value / price, 0.001)
```

### TP/SL Calculation
```python
atr_pct = atr_val / price
if signal == "BUY":
    tp = price * (1 + atr_pct * 2.5)
    sl = price * (1 - atr_pct * 1.5)
elif signal == "SELL":
    tp = price * (1 - atr_pct * 2.5)
    sl = price * (1 + atr_pct * 1.5)
```

### Daily Reset Logic
```python
if state['last_day'] != today:
    log_daily_summary(state['last_day'], state['day_start_equity'], state['equity'], state['daily_pnl'])
    state['daily_pnl'] = 0.0
    state['day_start_equity'] = state['equity']
    state['last_day'] = today
```

### TP/SL Check
```python
# For LONG
if current_price >= tp: hit = "TP", exit = tp
elif current_price <= sl: hit = "SL", exit = sl

# For SHORT
if current_price <= tp: hit = "TP", exit = tp
elif current_price >= sl: hit = "SL", exit = sl
```

### Correlation Filter
```python
same_direction = sum(1 for p in positions.values() if p['side'] == side)
if same_direction >= 2: reject_signal()
```

## Files Created
- `/data/crypto-trader/paper_trading_bot.py` - Full paper trading bot
- `/data/crypto-trader/paper_state.json` - Current state (equity, positions, trades)
- `/data/crypto-trader/paper_trades.json` - Trade log (append
- `/data/crypto-trader/paper_daily.json` - Daily summaries

## Cron Job Active
- Job ID: `98c19ca9181a`
- Name: `bitunix-paper-trading-2days`
- Schedule: `every 60m`
- Model: `{"model": "nvidiarail", "provider": "openai-api"}`
- Last run: 2026-07-27 08:08 UTC (status: OK)

## Telegram Reports
Token: `8825978198:AAE9H8mYFv2j5oFZKVuXOQLzxDFW3yZUCys`
Chat: `8048000483`
Format: HTML with emojis, portfolio summary, positions, signals, stats