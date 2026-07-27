# Bitunix Futures Order API - Working Implementation (2026-07-27)

## Correct Endpoints (from Java SDK)

### Place Order
- **Endpoint:** `POST /api/v1/futures/trade/place_order`
- **Body Parameters:**
  - `marginCoin` (string, required): "USDT"
  - `symbol` (string, required): e.g., "BTCUSDT"
  - `side` (string, required): "BUY" (long) or "SELL" (short)
  - `tradeSide` (string, required): "OPEN" (new position) or "CLOSE"
  - `orderType` (int, required): 1 = limit, 2 = market
  - `qty` (string, required): quantity as string
  - `price` (string, optional): required for limit orders

### Set TP/SL for Position
- **Endpoint:** `POST /api/v1/futures/tpsl/position/place_order`
- **Body Parameters:**
  - `symbol` (string, required)
  - `tpTriggerPrice` (string, optional): TP trigger price
  - `tpOrderPrice` (string, optional): TP order price (same as trigger for market)
  - `slTriggerPrice` (string, optional): SL trigger price
  - `slOrderPrice` (string, optional): SL order price
  - `qty` (string, optional): position quantity

### Close All Positions
- **Endpoint:** `POST /api/v1/futures/trade/close_all_position`
- **Body:** `{"symbol": "BTCUSDT"}`

### Get Positions
- **Endpoint:** `GET /api/v1/futures/position/current`
- **Params:** `symbol` (optional)
- **Note:** Returns 404 if no positions (not an error)

### Get Pending Orders
- **Endpoint:** `GET /api/v1/futures/trade/get_pending_orders`
- **Params:** `symbol` (optional)

### Cancel Order
- **Endpoint:** `POST /api/v1/futures/trade/cancel_orders`
- **Body:** `{"symbol": "BTCUSDT", "orderId": "12345"}`

## Signing for POST Requests

```python
# For POST, include body in signature
body_str = json.dumps(body, separators=(',', ':'), sort_keys=True)
sig_query = ""  # no query params for POST
digest = sha256(nonce + timestamp + api_key + sig_query + body_str)
sign = sha256(digest + secret)
```

## Working Test Results (2026-07-27)

| Test | Result | Notes |
|------|--------|-------|
| ETHUSDT BUY 0.01 | code=20003 | Insufficient balance = **signature correct** |
| ETHUSDT SELL 0.01 | code=20003 | Insufficient balance = **signature correct** |
| BTCUSDT 0.0001 | code=20003 | Insufficient balance = **signature correct** |
| Account endpoint | code=0 | ✅ Working |
| Positions endpoint | code=404 | ✅ Working (no positions) |
| Klines (public) | code=0 | ✅ Working |

## Test Script
`/data/crypto-trader/test_order_cycle.py` - Full order cycle test (place → TP/SL → verify → close)