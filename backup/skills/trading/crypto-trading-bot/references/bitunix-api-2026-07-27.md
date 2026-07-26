# Bitunix API Status — 2026-07-27

## ALL Endpoints Return 404

Every tested endpoint on `https://fapi.bitunix.com` returns `{"code":404,"data":null,"msg":"Not Found"}`:

### Tested Endpoints (all 404)
- `/api/v1/market/time`
- `/api/v1/market/ticker`
- `/api/v1/market/klines`
- `/api/v1/market/depth`
- `/api/v1/market/trades`
- `/api/v1/futures/account`
- `/api/v1/futures/position`
- `/api/v1/futures/order`
- `/api/v1/futures/trade`
- `/api/v1/public/time`
- `/api/v2/market/ticker`
- `/api/v2/futures/time`

### Partial Exception
- `/api/v1/futures/account` with authentication returns `{"code":1,"msg":"Network Error"}` — suggests endpoint exists but something blocks it (IP, auth, or network)

### Possible Causes
1. API version changed — need to check Bitunix docs for v2/v3
2. Server IP (152.55.177.142) blocked by Bitunix
3. API keys invalid or expired
4. Domain migration

### API Key Status
- Key: `4d1e490f251b883d4e89c989c2ab1db5`
- Secret: provided by user
- Both authenticated and unauthenticated requests fail
- User asked to generate new keys

### What Works
- Historical data files (provided by user locally) work fine
- Backtesting from local data works perfectly
- Paper trading bot logic works but can't fetch live data

### Next Steps
1. Check Bitunix API documentation for updated endpoints
2. Get new API keys from user
3. Test with fresh keys
4. If Bitunix API truly broken, consider Binance or Bybit as fallback
