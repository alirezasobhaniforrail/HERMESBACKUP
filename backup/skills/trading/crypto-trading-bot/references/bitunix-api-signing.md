# Bitunix API Signing Reference

## Authentication Method: Double SHA256 (NOT HMAC!)

Bitunix uses a UNIQUE signing method. Standard HMAC-SHA256 does NOT work.

## Headers (Required for All Private Endpoints)

```
api-key: <your_api_key>
nonce: <random_32_hex_string>
timestamp: <current_millis>
sign: <signature>
language: en-US
Content-Type: application/json
```

## Signature Algorithm

```python
import hashlib, secrets, time

def sha256_hex(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def sign_request(nonce, timestamp, api_key, query_params, body, secret_key):
    """
    Bitunix double-SHA256 signing method.
    
    Args:
        nonce: Random 32-char hex string (use secrets.token_hex(16))
        timestamp: Current time in milliseconds (13 digits)
        api_key: Your API key
        query_params: URL query string WITHOUT ? and WITHOUT encoding
                      Format: "key1value1key2value2" (sorted by key)
        body: Request body as string (empty "" for GET, JSON for POST)
        secret_key: Your secret key
    
    Returns:
        Hex signature string
    """
    # Step 1: Concatenate all parameters
    digest_input = nonce + timestamp + api_key + query_params + body
    
    # Step 2: First SHA256
    digest = sha256_hex(digest_input)
    
    # Step 3: Concatenate with secret key
    sign_input = digest + secret_key
    
    # Step 4: Second SHA256
    sign = sha256_hex(sign_input)
    
    return sign
```

## Query Params Format

**Pitfall**: Query params are NOT URL-encoded. Format is `key1value1key2value2`.

```python
# Correct:
query_params = "marginCoin=USDT"

# Multiple params (sorted by key):
query_params = "marginCoin=USDTsymbolBTCUSDT"

# For POST with body:
query_params = ""  # Empty if using body
body = '{"symbol":"BTCUSDT","side":"BUY","qty":"0.01"}'
```

## Working Examples

### Get Account Info (GET)
```python
import requests, json, time, hashlib, secrets

API_KEY = "your_api_key"
SECRET = "your_secret_key"
BASE = "https://fapi.bitunix.com"

nonce = secrets.token_hex(16)
timestamp = str(int(time.time() * 1000))
query_params = "marginCoin=USDT"
body = ""

digest = hashlib.sha256((nonce + timestamp + API_KEY + query_params + body).encode()).hexdigest()
sign = hashlib.sha256((digest + SECRET).encode()).hexdigest()

headers = {
    "api-key": API_KEY,
    "nonce": nonce,
    "timestamp": timestamp,
    "sign": sign,
    "language": "en-US",
    "Content-Type": "application/json"
}

r = requests.get(f"{BASE}/api/v1/futures/account?marginCoin=USDT", headers=headers)
print(r.json())
# Expected: {"code":0, "data":{...}, "msg":"Success"}
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Signature Error` (code 10007) | Wrong signing method | Use double SHA256, not HMAC |
| `Network Error` (code 1) | IP not bound | Add IP in "Bind IP address" field |
| `404 Not Found` | Wrong endpoint path | Check API docs for correct path |

## Known Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/futures/account?marginCoin=USDT` | Yes | Account info |
| GET | `/api/v1/market/klines` | No | Kline data |
| GET | `/api/v1/market/tickers` | No | All tickers |

## Debugging Tips

1. **Always check response code**: `code: 0` = success, anything else = error
2. **Test with minimal params**: Start with just `marginCoin=USDT`
3. **Verify timestamp**: Must be 13 digits (milliseconds)
4. **Check nonce**: Must be random, different for each request
5. **IP binding**: May take 1-2 minutes to activate after saving
