# Paper Trading Implementation - Bitunix Futures (2026-07-27 Session)

## Complete Working Paper Trading Bot

### File: `/data/crypto-trader/paper_trading_bot.py`

**Features:**
- Full position lifecycle management
- ATR-based TP/SL calculation
- Risk-based position sizing
- Correlation limits
- Daily PnL tracking
- Trade logging
- Telegram reporting
- State persistence

### Signal Generation (Implemented)

```python
def analyze_pair(api, symbol):
    # Fetch 1H (200 candles) and 4H (100 candles) klines
    # Calculate indicators:
    # 4H: EMA8, EMA25, EMA100, ADX14
    # 1H: RSI14, MACD(12,26,9), ATR14
    
    # Regime detection (using LAST CLOSED 4H candle only - look-ahead fix)
    if e8 > e25 > e100 and adx >= 20: regime = "BULL"
    elif e8 < e25 < e100 and adx >= 20: regime = "BEAR"
    else: regime = "RANGE"
    
    # Entry signals
    if regime == "BULL" and adx >= 20:
        if e8 > e25 and rsi > 45 and hist[i] > hist[i-1]: signal = "BUY"
    elif regime == "BEAR" and adx >= 20:
        if e8 < e25 and rsi < 55 and hist[i] < hist[i-1]: signal = "SELL"
    elif regime == "RANGE":
        if rsi < 30 and hist[i] > hist[i-1]: signal = "BUY"
        elif rsi > 70 and hist[i] < hist[i-1]: signal = "SELL"
    
    # TP/SL calculation
    if signal == "BUY":
        tp = price * (1 + atr_pct * 2.5)
        sl = price * (1 - atr_pct * 1.5)
    elif signal == "SELL":
        tp = price * (1 - atr_pct * 2.5)
        sl = price * (1 + atr_pct * 1.5)
```

### Position Sizing

```python
risk_amount = equity * 0.015  # 1.5%
sl_distance = abs(price - sl) / price
position_value = risk_amount / sl_distance
max_position_value = equity * 0.20
final_value = min(position_value, max_position_value)
size = final_value / price
```

### TP/SL Checking

```python
def check_tp_sl(state, api):
    for symbol, pos in state['positions'].items():
        current = api.get_price(symbol)
        if pos['side'] == "LONG":
            if current >= pos['tp']: hit = "TP"
            elif current <= pos['sl']: hit = "SL"
        else:  # SHORT
            if current <= pos['tp']: hit = "TP"
            elif current >= pos['sl']: hit = "SL"
        
        if hit:
            pnl = calc_pnl(pos, hit_price)
            state['equity'] += pnl
            state['daily_pnl'] += pnl
            log_trade(exit_trade)
            del state['positions'][symbol]
```

### State Management

**`paper_state.json`:**
```json
{
  "equity": 1000.0,
  "positions": {
    "BTCUSDT": {
      "symbol": "BTCUSDT",
      "side": "LONG",
      "entry": 64500.0,
      "size": 0.046,
      "tp": 65890.0,
      "sl": 63780.0,
      "entry_time": "2026-07-27T10:00:00",
      "leverage": 3
    }
  },
  "closed_trades": [...],
  "daily_pnl": 0.0,
  "day_start_equity": 1000.0,
  "last_day": "2026-07-27"
}
```

**`paper_trades.json`:** Array of all trades with entry/exit, PnL, duration, reason

**`paper_daily.json`:** Daily summaries with start/end equity, trade count, daily PnL

### Telegram Report Format

```html
📄 <b>Paper Trading Bot</b>
⏰ 2026-07-27 10:00:00
==============================

💰 <b>Paper Account:</b>
  Equity: $1,015.50
  Daily PnL: $+15.50
  Open Positions: 1/3
  Unrealized: $+8.20
  Total Value: $1,023.70

📊 <b>Open Positions:</b>
  BTCUSDT LONG @ $64,500
    Size: 0.046 | Current: $64,650
    PnL: +0.23% | TP: $65,890 | SL: $63,780

📈 <b>Market Scan:</b>
  ⚪ BTCUSDT: $64,650 | RANGE | ADX:12 | RSI:52
  🟢 ETHUSDT: $1,855 | BULL | ADX:22 | RSI:48 ⚡ BUY
  ...

🎯 <b>Executing 1 Signal(s):</b>
  ✅ BUY ETHUSDT @ $1,855
    Size: 1.62 | TP: $1,892 | SL: $1,834

📊 <b>Stats:</b>
  Total Trades: 5
  Win Rate: 80.0%
  Equity: $1,015.50
  Return: +1.55%
```

### Cron Job Configuration

```python
cronjob(
    action='create',
    name='bitunix-paper-trading-2days',
    schedule='every 60m',
    prompt='Run the Bitunix Paper Trading Bot. Execute: cd /data/crypto-trader && python3 paper_trading_bot.py.',
    model={"model": "nvidiarail", "provider": "openai-api"}
)
```

**Important:** Cron job MUST have explicit model config or fails with "no model configured"

### Verification Steps

1. **Manual run:** `cd /data/crypto-trader && python3 paper_trading_bot.py`
2. **Check Telegram:** Hourly message received
3. **Check state files:** `paper_state.json`, `paper_trades.json` updated
4. **Check cron:** `cronjob(action='list')` shows last_status: "ok"

### Known Working

- ✅ API connectivity (fapi.bitunix.com + openapi.bitunix.com)
- ✅ Signing method (double SHA256, marginCoinUSDT format)
- ✅ Market data (5 pairs: BTC, ETH, XRP, BNB, DOGE)
- ✅ Telegram delivery (every hour)
- ✅ State persistence (JSON files)
- ✅ Cron job execution (hourly, model configured)

### Ready for Live (After Paper Validation)

To go live:
1. Set `DRY_RUN = False` in `trading_bot.py`
2. Fund account with 1000 USDT
3. Add exchange-level STOP_MARKET orders after entry
4. Implement kill switch (DD > 20%)
5. Implement daily loss limit (-3%)