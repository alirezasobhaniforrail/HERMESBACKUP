# Bitunix API Reference

## Base URL
`https://fapi.bitunix.com`

## Public Endpoints (no auth)

### Klines (Candle Data)
```
GET /api/v1/futures/market/kline
Params: symbol, interval (1m/5m/15m/30m/1h/4h), limit (max 200), endTime (ms)
```

**CRITICAL: Pagination Direction**
- Response returns candles in REVERSE chronological order (newest first)
- To paginate backwards in time, use the LAST candle's timestamp for next `endTime`
- `batch[0]` = newest, `batch[-1]` = oldest

```python
# Paginating backwards through history
end_ms = int(time.time() * 1000)
while len(all_candles) < target:
    result = api._get_public('/api/v1/futures/market/kline', {
        'symbol': 'BTCUSDT', 'interval': '30m',
        'limit': '200', 'endTime': str(end_ms)
    })
    batch = result['data']
    # batch[0] is NEWEST, batch[-1] is OLDEST
    all_candles.extend(parse_batch(batch))
    end_ms = batch[-1]['time'] - 1  # Use OLDEST for next page
```

### Tickers
```
GET /api/v1/futures/market/tickers
Returns all symbols with lastPrice, high, low, markPrice, quoteVol
```

### Contracts (Symbol Info)
```
GET /api/v1/futures/market/contracts
Params: symbol
Returns: minOrderQty, maxMarketOrderVolume, basePrecision, quotePrecision
```

## Private Endpoints (require auth)

### Authentication Headers
```python
nonce = uuid4().hex
timestamp = str(int(time.time() * 1000))
digest = sha256(nonce + timestamp + api_key + query_params + body)
sign = sha256(digest + secret_key)
headers = {'api-key': api_key, 'sign': sign, 'nonce': nonce, 'timestamp': timestamp}
```

### Account Balance
```
GET /api/v1/futures/account
Params: marginCoin=USDT
Returns: available, frozen, margin, crossUnrealizedPNL
```

### Place Order
```
POST /api/v1/futures/trade/place_order
Body: {symbol, side (BUY/SELL), tradeSide (OPEN/CLOSE), orderType (MARKET/LIMIT), qty, price?}
```

### Close Position
```
POST /api/v1/futures/trade/place_order
Body: {symbol, side (opposite), tradeSide: "CLOSE", reduceOnly: true}
```

### Get Positions
```
GET /api/v1/futures/position/get_pending_positions
Params: symbol (optional)
```

## Known Issues
- Max 200 candles per request
- Timeout issues on some pairs (SOLUSDT, XRPUSDT) - increase timeout to 30s
- Port 22 often blocked on cloud servers - use HTTPS with PAT for git operations
