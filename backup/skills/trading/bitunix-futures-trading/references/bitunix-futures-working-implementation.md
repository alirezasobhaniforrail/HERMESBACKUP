# Bitunix Futures Working Implementation (2026-07-27 Session)

## Summary
This session successfully built and deployed a working Bitunix Futures paper trading bot with real API connectivity, Telegram notifications, and hourly cron job.

## Key Files Created

### `/data/crypto-trader/paper_trading_bot.py` (20KB)
Complete paper trading bot with:
- Full position management (open, close, TP/SL tracking)
- ATR-based TP/SL (2.5x TP, 1.5x SL)
- Risk-based position sizing (1.5% risk, 20% max position, 3 max concurrent)
- Correlation limits (max 2 same-direction)
- Daily PnL reset with date-based logic
- Trade logging to JSON
- Daily summary logging
- Telegram HTML reports every hour
- State persistence to JSON files

### `/data/crypto-trader/trading_bot.py` (15KB)
Live trading bot template (DRY_RUN=True by default) with:
- Same signal logic as paper bot
- Order execution with TP/SL placement
- Telegram notifications
- Account/position checking

### `/data/crypto-trader/bitunix_futures.py` (5KB)
Minimal API client for futures:
- Double SHA256 signing (NOT HMAC)
- GET/POST helpers
- Account, positions, order placement, TP/SL, close

### `/data/crypto-trader/bot_config_final.json`
Configuration with API keys:
```json
{
  "api_key": "eb5ae57ec67a67eb4999080e5d6d3f02",
  "secret_key": "1540be622a086e8e74afa25c012fae28",
  "dry_run": true
}
```

## Critical API Discoveries

### Signing Method (Working)
```python
# For signature: "marginCoinUSDT" (NO equals)
# For URL: "marginCoin=USDT" (WITH equals)

def _signed_get(self, endpoint, params_str=""):
    # params_str = "marginCoinUSDT"
    # For signature: use as-is
    # For URL: find "USDT" index, insert "="
    idx = params_str.rfind("USDT")
    url_params = params_str[:idx] + "=" + params_str[idx:]
```

### Endpoints (Verified Working)
- `GET https://fapi.bitunix.com/api/v1/futures/account?marginCoin=USDT` (30s timeout)
- `GET https://fapi.bitunix.com/api/v1/futures/position/current`
- Market data: `GET https://openapi.bitunix.com/api/spot/v1/market/kline?symbol=BTCUSDT&interval=60`

### Headers Required
```
api-key: <key>
nonce: <32-char hex>
timestamp: <ms since epoch>
sign: <double SHA256>
language: en-US
Content-Type: application/json
```

### Timeout Critical
- Account endpoint REQUIRES 30s timeout (10s fails with "Network Error")

## Signal Logic (Implemented)
- **4H Regime**: EMA 8/25/100 + ADX ≥ 20 → BULL/BEAR/RANGE
- **1H Entry**: RSI + MACD histogram momentum
- **BULL Long**: EMA8 > EMA25 + RSI > 45 + MACD hist rising
- **BEAR Short**: EMA8 < EMA25 + RSI < 55 + MACD hist falling
- **RANGE Long**: RSI < 30 + MACD hist rising
- **RANGE Short**: RSI > 70 + MACD hist falling
- **Look-ahead fix**: Only use CLOSED 4H candles

## Telegram Integration
- Token: `8825978198:AAE9H8mYFv2j5oFZKVuXOQLzxDFW3yZUCys`
- Chat ID: `8048000483`
- HTML formatted hourly reports
- Reports include: account, positions, market scan, signals, stats

## Cron Job (Active)
```bash
# Job ID: 98c19ca9181a
# Name: bitunix-paper-trading-2days
# Schedule: every 60m
# Model: nvidiarail / openai-api
# Last status: OK
```

## State Files
- `paper_state.json` - Equity, positions, closed trades, daily PnL
- `paper_trades.json` - All trade entries/exits with PnL
- `paper_daily.json` - Daily summaries

## Next Steps for Live Deployment
1. Verify paper trading results for 48 hours
2. Set `DRY_RUN = False` in trading_bot.py
3. Fund account with 1000 USDT
4. Add exchange-level STOP_MARKET orders
5. Implement kill switch and daily loss limits