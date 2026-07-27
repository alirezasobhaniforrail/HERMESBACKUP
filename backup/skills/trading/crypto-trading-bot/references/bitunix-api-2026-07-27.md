# Bitunix API Status — 2026-07-27 (Updated)

## Status: BROKEN — All Endpoints Return 404 or "Network Error"

### Tested Base URLs
| URL | Status | Notes |
|-----|--------|-------|
| `https://fapi.bitunix.com` | Partial | Account endpoint exists but returns "Network Error" |
| `https://www.bitunix.com` | 404 | SPA frontend, not API |
| `https://api.bitunix.com` | 403 | Blocked |

### Authenticated Endpoint (`/api/v1/futures/account`)
- Returns `{"code":1,"msg":"Network Error"}` when IP not bound
- With new API key + IP binding: STILL returns "Network Error"
- Possible cause: IP binding format issue or server-side block

### Public Endpoints (all 404)
- `/api/v1/market/ticker` — 404
- `/api/v1/market/klines` — 404
- `/api/v1/market/depth` — 404
- `/api/v1/market/trades` — 404
- `/api/v2/market/ticker` — 404

### API Key Status (2026-07-27)
- Key: `eb5ae57ec67a67eb4999080e5d6d3f02`
- Secret: `1540be622a086e8e74afa25c012fae28`
- IP Binding: `152.55.177.142` (applied via "Bind IP address" field)
- Permission: Trade (read-only not available)
- Result: "Network Error" on authenticated endpoints

### Official Documentation
- Docs URL: `https://openapidoc.bitunix.com/doc/common/introduction.html`
- GitHub: `https://github.com/BitunixOfficial/open-api`
- Sign docs: `https://openapidoc.bitunix.com/doc/futures/common/sign.html`
- Base URL per docs: `https://www.bitunix.com/api`
- Docs are SPA (VitePress) — cannot scrape, need browser

### Signing Method (from docs)
1. Collect all params + timestamp (ms)
2. Sort params alphabetically
3. Create query string: key1=val1&key2=val2&...
4. Sign: HMAC-SHA256(secret_key, query_string)
5. Append: &signature=hex_signature
6. Header: X-BX-APIKEY: api_key

### What Works
- Historical data files (provided by user locally)
- Backtesting from local data
- Paper trading bot logic (but no live data feed)

### Fallback Options
1. Check Bitunix docs in browser for updated endpoints
2. Use Binance API (better documented, more reliable)
3. Use Bybit API (similar to Bitunix)
4. Wait for Bitunix API update

### Known Issues
- API endpoints changed between versions (v1 to v2?)
- IP binding may require specific format
- "Network Error" is ambiguous — could be IP block, auth issue, or endpoint change
- No public market data endpoints working
