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

### Safety
- DRY_RUN = True by default
- Max position size limits
- Daily loss limits
- Kill switch on drawdown