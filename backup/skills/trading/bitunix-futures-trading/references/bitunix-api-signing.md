# Bitunix Futures API Signing Reference

## Overview
Double SHA256 signature scheme used by Bitunix Futures API (`fapi.bitunix.com`).

## Signature Algorithm

```python
import hashlib
import secrets
import time

def sign_request(api_key, secret_key, params_str="", body_str=""):
    """
    Generate Bitunix Futures API signature.
    
    Args:
        api_key: Your API key
        secret_key: Your API secret
        params_str: Query parameters WITHOUT equals signs (e.g., "marginCoinUSDT")
        body_str: Request body JSON string (alphabetically sorted keys, no spaces)
    
    Returns:
        dict: headers with api-key, nonce, timestamp, sign
    """
    timestamp = str(int(time.time() * 1000))
    nonce = secrets.token_hex(16)
    
    # CRITICAL: params_str uses NO equals signs for signing
    # Example: "marginCoinUSDT" not "marginCoin=USDT"
    message = nonce + timestamp + api_key + params_str + body_str
    
    # Double SHA256
    digest = hashlib.sha256(message.encode('utf-8')).hexdigest()
    sign = hashlib.sha256((digest + secret_key).encode('utf-8')).hexdigest()
    
    return {
        'api-key': api_key,
        'nonce': nonce,
        'timestamp': timestamp,
        'sign': sign,
        'language': 'en-US',
        'Content-Type': 'application/json'
    }
```

## Parameter Format Quirk (CRITICAL)

| Usage | Format | Example |
|-------|--------|---------|
| **Signature** | No equals | `marginCoinUSDT` |
| **URL Query** | With equals | `marginCoin=USDT` |

This applies to ALL query parameters.

## Common Endpoints & Parameters

### GET /api/v1/futures/account
- **Signature params:** `marginCoinUSDT`
- **URL params:** `marginCoin=USDT`

### GET /api/v1/futures/position/current
- **Signature params:** `` (empty)
- **URL params:** `` (empty)

### GET /api/v1/futures/order/pending
- **Signature params:** `symbolBTCUSDT`
- **URL params:** `symbol=BTCUSDT`

### POST /api/v1/futures/order/place_order
- **Signature params:** `` (empty - body only)
- **Body:** JSON with sorted keys, no spaces

```json
{
  "symbol": "BTCUSDT",
  "side": 1,
  "type": 2,
  "size": "1",
  "price": "0"
}
```

### POST /api/v1/futures/tpsl/position_tpsl_order
- **Signature params:** `` (empty - body only)
- **Body:**
```json
{
  "symbol": "BTCUSDT",
  "tpTriggerPrice": "65000",
  "tpOrderPrice": "65000",
  "slTriggerPrice": "63000",
  "slOrderPrice": "63000",
  "size": "1"
}
```

## Python Implementation

```python
import hashlib
import secrets
import time
import requests
import json

class BitunixFutures:
    BASE_URL = "https://fapi.bitunix.com"
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def _sign(self, params_str="", body_str=""):
        timestamp = str(int(time.time() * 1000))
        nonce = secrets.token_hex(16)
        
        message = nonce + timestamp + self.api_key + params_str + body_str
        digest = hashlib.sha256(message.encode()).hexdigest()
        sign = hashlib.sha256((digest + self.api_secret).encode()).hexdigest()
        
        return {
            'api-key': self.api_key,
            'nonce': nonce,
            'timestamp': timestamp,
            'sign': sign,
            'language': 'en-US',
            'Content-Type': 'application/json'
        }
    
    def _convert_params(self, params_str):
        """Convert 'marginCoinUSDT' -> 'marginCoin=USDT' for URL"""
        if not params_str or '=' in params_str:
            return params_str
        # Find USDT suffix
        idx = params_str.rfind("USDT")
        if idx > 0:
            return params_str[:idx] + "=" + params_str[idx:]
        return params_str
    
    def get(self, endpoint, params_str=""):
        headers = self._sign(params_str)
        url_params = self._convert_params(params_str)
        url = f"{self.BASE_URL}{endpoint}"
        if url_params:
            url += "?" + url_params
        return requests.get(url, headers=headers, timeout=30).json()
    
    def post(self, endpoint, data=None):
        body = json.dumps(data, separators=(',', ':'), sort_keys=True) if data else ""
        headers = self._sign(body_str=body)
        return requests.post(f"{self.BASE_URL}{endpoint}", data=body, headers=headers, timeout=30).json()

# Usage
client = BitunixFutures(API_KEY, SECRET)
account = client.get("/api/v1/futures/account", "marginCoinUSDT")
positions = client.get("/api/v1/futures/position/current")
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `code: 10007, msg: "Signature Error"` | Wrong param format in signature | Use `marginCoinUSDT` not `marginCoin=USDT` |
| `code: 1, msg: "Network Error"` | Timeout too short | Use 30s timeout for account endpoint |
| `status: 404` | Wrong base URL | Use `fapi.bitunix.com` not `openapi.bitunix.com` |