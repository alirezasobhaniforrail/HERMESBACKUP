---
name: bitunix-futures-trading
description: Build Bitunix Futures bots with API signing and indicators.
category: trading
---

# Bitunix Futures Trading Bot Development

Class-level skill for building automated trading bots on Bitunix Futures.

## Key Technical Discoveries

### Bitunix Futures API Signing
**Base URL:** `https://fapi.bitunix.com`

**Signature Method (Double SHA256):**
```python
sig_params = "marginCoinUSDT"  # NO equals sign for signature
digest = sha256(nonce + timestamp + api_key + sig_params)
sign = sha256(digest + secret_key)

url_params = "marginCoin=USDT"  # WITH equals for URL
```

**Headers:** api-key, nonce, timestamp, sign, language: en-US, Content-Type: application/json

**Critical:** Signature uses params WITHOUT `=`, URL uses params WITH `=`.

**Timeout:** Use 30s for `/api/v1/futures/account`.

**Parameter Parsing Fix (2026-07-26):** The `_convert_params` method must handle specific param patterns:
- `marginCoinUSDT` → `marginCoin=USDT` (8-char suffix "CoinUSDT")
- `symbolBTCUSDT` → `symbol=BTCUSDT` (4-char suffix "USDT")

### Endpoints
- `/api/v1/futures/account` - GET account balance
- `/api/v1/futures/position/current` - GET positions
- `/api/v1/futures/order/place_order` - POST orders
- `/api/v1/futures/tpsl/position_tpsl_order` - POST TP/SL

### Market Data
Uses Spot API: `https://openapi.bitunix.com/api/spot/v1/market/kline`

### Trading Bot Components
1. BitunixFutures class - API client with signing
2. Indicators - EMA, RSI, ADX, MACD, ATR
3. Signal generator - Regime detection + entry rules
4. TP/SL calculator - ATR-based (2.5x TP, 1.5x SL)
5. Telegram notifier - HTML reports
6. State persistence - JSON files
7. Cron scheduler - Hourly via Hermes cron

### Signal Logic
- 4H: EMA 8/25/100 + ADX for regime
- 1H: RSI + MACD histogram for entry
- ADX >= 20 required for trend signals
- Range: RSI < 30 (buy) / > 70 (sell) with MACD confirmation

### Refined Signal Logic (2026-07-26)
- Range RSI thresholds: 30/70 (wider bands)
- MACD histogram momentum confirmation: `hist[i] > hist[i-1]`
- Bull/Bear RSI filters: 45/55 (stronger momentum required)
- ADX >= 20 filter on all regimes

### Safety
- DRY_RUN = True by default
- Max position size limits
- Daily loss limits
- Kill switch on drawdown

### Paper Trading Implementation (2026-07-26)
Full paper trading bot with:
- Position management (open/close/TP/SL tracking)
- Daily PnL reset with date-based logic
- Correlation limits (max 2 same-direction positions)
- Risk-based position sizing (1.5% risk per trade, 20% max per position, 3 max positions)
- ATR-based TP/SL (2.5x TP, 1.5x SL)
- Full trade logging (entries, exits, PnL, duration)
- Daily summary logging
- Telegram hourly reports with portfolio value, positions, signals, stats

## Working Implementation (2026-07-27 - THIS SESSION)
**BitunixFutures class** (`/data/crypto-trader/trading_bot.py` and `paper_trading_bot.py`):
- Correct API signing: `marginCoinUSDT` for signature, `marginCoin=USDT` for URL
- Working endpoints on `https://fapi.bitunix.com`:
  - `GET /api/v1/futures/account?marginCoin=USDT` (30s timeout)
  - `GET /api/v1/futures/position/current`
  - Market data via `https://openapi.bitunix.com/api/spot/v1/market/kline`
- Parameter parsing: `idx = params_str.rfind("USDT")` then `params_str[:idx] + "=" + params_str[idx:]`
- Timeout: 30s for account endpoint (critical)

**Files:**
- `/data/crypto-trader/trading_bot.py` - Live bot template (DRY_RUN=True)
- `/data/crypto-trader/paper_trading_bot.py` - Full paper trading with TP/SL tracking
- `/data/crypto-trader/bitunix_futures.py` - Minimal API client
- `/data/crypto-trader/bot_config_final.json` - API keys stored
- `/data/crypto-trader/paper_state.json` - Paper trading state
- `/data/crypto-trader/paper_trades.json` - Trade log
- `/data/crypto-trader/paper_daily.json` - Daily summaries

**Cron Job Active:**
- Job ID: `98c19ca9181a`
- Name: `bitunix-paper-trading-2days`
- Schedule: `every 60m`
- Model: `{"model": "nvidiarail", "provider": "openai-api"}` (EXPLICIT MODEL REQUIRED)
- Last status: OK (last run 2026-07-27 08:08 UTC)

**Telegram:**
- Token: `8825978198:AAE9H8mYFv2j5oFZKVuXOQLzxDFW3yZUCys`
- Chat: `8048000483`
- Hourly reports working with: account equity, open positions, market scan (5 pairs), signals, stats

## Session 2026-07-27 Key Learnings

### 1. Cron Job Model Configuration (CRITICAL)
Cron jobs fail with "no model configured" unless explicitly set:
```python
cronjob(
    action='update',
    job_id='98c19ca9181a',
    model={"model": "nvidiarail", "provider": "openai-api"}
)
```

### 2. Paper Trading Bot Features (Complete)
- Position management (open/close/TP/SL tracking)
- Daily PnL reset with date-based logic
- Correlation limits (max 2 same-direction positions)
- Risk-based position sizing (1.5% risk per trade, 20% max per position, 3 max positions)
- ATR-based TP/SL (2.5x TP, 1.5x SL)
- Full trade logging (entries, exits, PnL, duration)
- Daily summary logging
- Telegram hourly reports with portfolio value, positions, signals, stats
- State persistence to JSON files

### 3. API Signing Edge Cases Resolved
- **Parameter parsing bug fixed:** `rfind("USDT")` was incorrectly parsing `marginCoinUSDT` → `margin=CoinUSDT`. Fixed with exact suffix matching:
  - `endswith("CoinUSDT")` → `[:-8] + "=" + [-8:]` (marginCoin=USDT)
  - `endswith("USDT")` → `[:-4] + "=" + [-4:]` (symbol=BTCUSDT)
- **30s timeout mandatory** for `/api/v1/futures/account` endpoint
- **Base URL:** `fapi.bitunix.com` for private, `openapi.bitunix.com` for market data

### 4. Futures Order Placement - WORKING IMPLEMENTATION (2026-07-27)
**Correct Endpoint:** `/api/v1/futures/trade/place_order` (NOT `/api/v1/futures/order/place_order`)

**Correct Request Body Format:**
```python
body = {
    "marginCoin": "USDT",      # REQUIRED
    "symbol": "BTCUSDT",
    "side": "BUY",             # "BUY" for long, "SELL" for short
    "tradeSide": "OPEN",       # "OPEN" for new position
    "orderType": 2,            # 1=limit, 2=market
    "qty": "0.001"             # string, NOT size
}
```

**Critical Fields from Java SDK:**
- `marginCoin` - required in body (not query params)
- `side` - "BUY"/"SELL" (NOT 1/2)
- `tradeSide` - "OPEN"/"CLOSE" (required)
- `orderType` - 1=limit, 2=market (NOT type)
- `qty` - string quantity (NOT size)

**Signature for POST:** Body MUST be included in signature:
```python
sig_query = ""  # no query params for POST
body_str = json.dumps(body, separators=(',', ':'), sort_keys=True)
digest = sha256(nonce + timestamp + api_key + sig_query + body_str)
sign = sha256(digest + secret)
```

**Working Test Results:**
- ETHUSDT BUY 0.01 → `code=20003` (Insufficient balance) = **SIGNATURE CORRECT**
- ETHUSDT SELL 0.01 → `code=20003` = **SIGNATURE CORRECT**
- BTCUSDT 0.0001 → `code=20003` = **SIGNATURE CORRECT**

### 5. Order Cycle Test Script Created
`/data/crypto-trader/test_order_cycle.py` - Tests full cycle:
1. Place market order
2. Set TP/SL
3. Verify position via API
4. Close position
5. Repeat 10x across 5 pairs

### 6. TP/SL Endpoint
- `/api/v1/futures/tpsl/position/place_order`
- Body: `symbol`, `tpTriggerPrice`, `tpOrderPrice`, `slTriggerPrice`, `slOrderPrice`, `qty`

### 7. Positions Endpoint
- `/api/v1/futures/position/current` - returns 404 if no positions (not error)
- `/api/v1/futures/trade/close_all_position` - closes all positions for symbol

### 8. Order Cancellation
- `/api/v1/futures/trade/cancel_orders` - body: `symbol`, `orderId`

### 9. Pending Orders
- `/api/v1/futures/trade/get_pending_orders`

### 10. Market Data
- Spot klines: `https://openapi.bitunix.com/api/spot/v1/market/kline` with `interval`: "60" (1H), "240" (4H)
- Price ticker: `https://openapi.bitunix.com/api/spot/v1/market/tickers`

## Session 2026-07-27 Additional Learnings

### 11. Bitunix SDK (Spot Only) Working
```python
from bitunix import BitunixClient
client = BitunixClient(api_key="KEY", api_secret="SECRET")
ticker = client.get_latest_price("BTCUSDT")  # {'data': '64697.99'}
klines = client.get_kline_data("BTCUSDT", "60")  # 60=1H, 240=4H
balance = client.get_account_balance()
```
- SDK handles auth for SPOT endpoints only
- Base URL: `https://openapi.bitunix.com`
- Interval format: minutes as strings ("60" not "1H")

### 12. Parameter Signing - Critical Difference for POST vs GET
- **GET**: Signature uses query params without `=` (e.g., `marginCoinUSDT`), URL uses with `=` (e.g., `marginCoin=USDT`)
- **POST**: Signature uses JSON body string (sorted keys, no spaces), no query params in signature
- The `sig_query` for POST should be empty string `""`

### 13. Order Response Codes
- `code=0` - Success
- `code=2` - Parameter error (wrong field names/values)
- `code=20003` - Insufficient balance (signature correct, just no funds)
- `code=10007` - Signature error
- `code=1` - Network error
- `code=404` - Endpoint not found
- `code=20008` - Parameter validation failed (e.g., BUY must be OPEN/CLOSE)

### 14. Complete Working Endpoints (Futures)
| Operation | Endpoint | Method |
|-----------|----------|--------|
| Account | `/api/v1/futures/account` | GET |
| Positions | `/api/v1/futures/position/current` | GET |
| Place Order | `/api/v1/futures/trade/place_order` | POST |
| Set TP/SL | `/api/v1/futures/tpsl/position/place_order` | POST |
| Close All | `/api/v1/futures/trade/close_all_position` | POST |
| Cancel Order | `/api/v1/futures/trade/cancel_orders` | POST |
| Pending Orders | `/api/v1/futures/trade/get_pending_orders` | GET |
| History Orders | `/api/v1/futures/trade/get_history_orders` | GET |
| History Trades | `/api/v1/futures/trade/get_history_trades` | GET |
| Order Detail | `/api/v1/futures/trade/get_order_detail` | GET |

### 15. Paper Trading Cron Job Active
- Job ID: `98c19ca9181a`
- Name: `bitunix-paper-trading-2days`
- Schedule: `every 60m`
- Model: `{"model": "nvidiarail", "provider": "openai-api"}`
- Last status: OK
- Runs: `cd /data/crypto-trader && python3 paper_trading_bot.py`

### 16. Communication Rules (from user correction - MANDATORY)
When working with Ali:
1. Call him "Ali" (علی) - not "user" or "you"
2. Be logical, no cheerleading or enthusiasm
3. NEVER agree just to confirm - only say if path is correct or wrong
4. Act as expert assistant, not a yes-man
5. Check things from overlooked angles BEFORE responding
6. Be direct and critical when something is wrong
7. Present facts, let user decide

**Critical Rule**: User said "مسیر رو پیش نبر فقط بگو مسیر درسته یا غلط" - NEVER advance the path just to confirm. Only say if it's correct or wrong.

## References
- `references/bitunix-api-signing.md` - API signing details and common errors
- `references/indicator-formulas.md` - Pure Python indicator implementations
- `references/paper-trading-implementation.md` - Complete paper trading logic
- `references/telegram-format.md` - Telegram message formatting
- `references/bitunix-price-api-fix.md` - Ticker endpoint 404 fix using klines
- `references/session-2026-07-28-learnings.md` - Session 2026-07-28 debugging and validation

## Templates
- `templates/trading_bot_template.py` - Live trading bot template
- `templates/paper_trading_bot.py` - Complete paper trading bot

## Cron Configuration
```python
cronjob(
    action='create',
    name='bitunix-paper-trading-2days',
    schedule='every 60m',
    prompt='Run the Bitunix Paper Trading Bot. Execute: cd /data/crypto-trader && python3 paper_trading_bot.py.',
    model={"model": "nvidiarail", "provider": "openai-api"}
)
```

**Critical:** Cron jobs MUST have explicit model configuration or they fail with "no model configured".