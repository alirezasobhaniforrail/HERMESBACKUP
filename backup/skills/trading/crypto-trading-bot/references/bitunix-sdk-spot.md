# Bitunix Python SDK — Spot API Reference

## Installation
```bash
pip install bitunix
```

## Available Methods
```python
from bitunix import BitunixClient

client = BitunixClient(api_key="YOUR_KEY", api_secret="YOUR_SECRET")

# Public
client.get_latest_price("BTCUSDT")     # {'data': '64697.99'}
client.get_kline_data("BTCUSDT", "60")  # 60=1H, 240=4H
client.get_trading_pairs()              # Full pair list
client.get_depth_data("BTCUSDT")        # Order book
client.get_rate_data()                  # Rate/fee info
client.get_token_data()                 # Token details

# Private
client.get_account_balance()            # Spot balance
client.place_order(side=2, ...)         # 1=Sell, 2=Buy
client.place_batch_orders([...])        # Batch orders
client.cancel_orders([...])             # Cancel by ID
client.query_current_orders("BTCUSDT")  # Open orders
client.query_order_history("BTCUSDT")   # Past orders
client.query_matching_orders(order_id, symbol)  # Fills
```

## Kline Interval Format
The SDK uses MINUTES as strings, not human-readable:
- `"1"` = 1 minute
- `"5"` = 5 minutes
- `"15"` = 15 minutes
- `"30"` = 30 minutes
- `"60"` = 1 hour (1H)
- `"120"` = 2 hours
- `"240"` = 4 hours (4H)
- `"360"` = 6 hours
- `"720"` = 12 hours
- `"D"` = 1 day
- `"M"` = 1 month
- `"W"` = 1 week

## Kline Response Format
```json
{
  "symbol": "BTCUSDT",
  "open": "64649.03",
  "high": "64750.98",
  "low": "64649.03",
  "close": "64750.98",
  "volume": "7.47632",
  "ts": "2026-07-26T21:00:00Z"
}
```

## Pitfalls
1. **SPOT only** — no futures endpoints
2. **Different base URL** — `openapi.bitunix.com` (not `fapi.bitunix.com`)
3. **Account balance returns `data: None`** when spot account is empty (not an error)
4. **Kline params**: `symbol` and `interval` are required, `limit` is NOT a parameter

## Base URL
```
https://openapi.bitunix.com
```

## Signing (handled internally)
The SDK handles authentication internally using double-SHA256 signing. No manual signing needed for spot endpoints.
