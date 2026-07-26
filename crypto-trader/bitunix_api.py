"""
Bitunix Futures API Client - Official Format
Base URL: https://fapi.bitunix.com
"""
import hashlib
import json
import time
import uuid
import requests


def get_nonce():
    return str(uuid.uuid4()).replace('-', '')


def get_timestamp():
    return str(int(time.time() * 1000))


def sort_params(params):
    """Sort params and concatenate as key+value pairs (no separators)"""
    if not params:
        return ''
    return ''.join(f"{k}{v}" for k, v in sorted(params.items()))


def generate_signature(api_key, secret_key, nonce, timestamp, query_params='', body=''):
    """Bitunix double SHA-256 signature"""
    digest_input = nonce + timestamp + api_key + query_params + body
    digest = hashlib.sha256(digest_input.encode('utf-8')).hexdigest()
    sign = hashlib.sha256((digest + secret_key).encode('utf-8')).hexdigest()
    return sign


def get_auth_headers(api_key, secret_key, query_params='', body=''):
    nonce = get_nonce()
    timestamp = get_timestamp()
    sign = generate_signature(api_key, secret_key, nonce, timestamp, query_params, body)
    return {
        'api-key': api_key,
        'sign': sign,
        'nonce': nonce,
        'timestamp': timestamp,
    }


class BitunixAPI:
    BASE_URL = 'https://fapi.bitunix.com'

    def __init__(self, api_key='', secret_key=''):
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'language': 'en-US',
        })

    def _get_public(self, path, params=None):
        url = self.BASE_URL + path
        try:
            r = self.session.get(url, params=params, timeout=15)
            return r.json()
        except Exception as e:
            return {'code': -1, 'msg': str(e), 'data': None}

    def _get_private(self, path, params=None):
        url = self.BASE_URL + path
        params = params or {}
        query_string = sort_params(params)
        headers = get_auth_headers(self.api_key, self.secret_key, query_string)
        try:
            r = self.session.get(url, params=params, headers=headers, timeout=15)
            return r.json()
        except Exception as e:
            return {'code': -1, 'msg': str(e), 'data': None}

    def _post_private(self, path, data=None):
        url = self.BASE_URL + path
        body_str = json.dumps(data, separators=(',', ':')) if data else ''
        headers = get_auth_headers(self.api_key, self.secret_key, '', body_str)
        try:
            r = self.session.post(url, data=body_str, headers=headers, timeout=15)
            return r.json()
        except Exception as e:
            return {'code': -1, 'msg': str(e), 'data': None}

    # ==================== MARKET DATA ====================

    def get_klines(self, symbol='BTCUSDT', interval='30m', limit=200, start_time=None, end_time=None):
        all_candles = []
        remaining = limit
        st = start_time
        while remaining > 0:
            batch_size = min(remaining, 200)
            params = {'symbol': symbol, 'interval': interval, 'limit': str(batch_size)}
            if st: params['startTime'] = str(st)
            if end_time: params['endTime'] = str(end_time)
            result = self._get_public('/api/v1/futures/market/kline', params)
            if result.get('code') == 0 and result.get('data'):
                batch = []
                for c in result['data']:
                    batch.append({
                        'timestamp': int(c['time']) // 1000,
                        'open': float(c['open']),
                        'high': float(c['high']),
                        'low': float(c['low']),
                        'close': float(c['close']),
                        'volume': float(c.get('quoteVol', 0)),
                    })
                if not batch: break
                all_candles.extend(batch)
                remaining -= len(batch)
                st = (batch[0]['timestamp'] - 1) * 1000
                if len(batch) < batch_size: break
                time.sleep(0.2)
            else:
                break
        all_candles.sort(key=lambda x: x['timestamp'])
        seen = set(); unique = []
        for c in all_candles:
            if c['timestamp'] not in seen:
                seen.add(c['timestamp']); unique.append(c)
        return unique

    def get_ticker(self, symbol='BTCUSDT'):
        result = self._get_public('/api/v1/futures/market/tickers')
        if result.get('code') == 0 and result.get('data'):
            for t in result['data']:
                if t.get('symbol') == symbol:
                    return {
                        'symbol': symbol,
                        'last': float(t.get('lastPrice', 0)),
                        'high': float(t.get('high', 0)),
                        'low': float(t.get('low', 0)),
                        'volume': float(t.get('quoteVol', 0)),
                        'mark_price': float(t.get('markPrice', 0)),
                    }
        return None

    # ==================== ACCOUNT ====================

    def get_balance(self, margin_coin='USDT'):
        result = self._get_private('/api/v1/futures/account', {'marginCoin': margin_coin})
        if result.get('code') == 0 and result.get('data'):
            d = result['data']
            available = float(d.get('available', 0))
            frozen = float(d.get('frozen', 0))
            margin = float(d.get('margin', 0))
            bonus = float(d.get('bonus', 0))
            upnl = float(d.get('crossUnrealizedPNL', 0)) or float(d.get('isolationUnrealizedPNL', 0))
            equity = available + margin + upnl + bonus
            return {
                'equity': equity,
                'available': available,
                'unrealized_pnl': upnl,
                'margin': margin,
                'frozen': frozen,
                'bonus': bonus,
            }
        return None

    def get_positions(self, symbol=None):
        params = {}
        if symbol: params['symbol'] = symbol
        result = self._get_private('/api/v1/futures/position/get_pending_positions', params)
        if result.get('code') == 0 and result.get('data'):
            positions = []
            for p in result['data']:
                positions.append({
                    'symbol': p.get('symbol'),
                    'side': p.get('side'),
                    'size': float(p.get('qty', 0)),
                    'entry_price': float(p.get('avgOpenPrice', 0)),
                    'mark_price': float(p.get('markPrice', 0)),
                    'unrealized_pnl': float(p.get('unrealizedPNL', 0)),
                    'leverage': int(p.get('leverage', 1)),
                    'position_id': p.get('positionId', ''),
                    'margin_mode': p.get('marginMode', 'CROSSED'),
                })
            return positions
        return []

    # ==================== TRADING ====================

    def set_leverage(self, symbol='BTCUSDT', leverage=10, margin_mode='CROSSED'):
        self._post_private('/api/v1/futures/account/change_margin_mode', {
            'symbol': symbol, 'marginMode': margin_mode, 'marginCoin': 'USDT'
        })
        result = self._post_private('/api/v1/futures/account/change_leverage', {
            'symbol': symbol, 'leverage': str(leverage), 'marginCoin': 'USDT'
        })
        return result

    def place_market_order(self, symbol='BTCUSDT', side='BUY', qty=0.001, trade_side='OPEN', reduce_only=False, tp_price=None, sl_price=None, position_id=None):
        data = {
            'symbol': symbol,
            'side': side,
            'tradeSide': trade_side,
            'orderType': 'MARKET',
            'qty': str(qty),
        }
        if reduce_only:
            data['reduceOnly'] = True
        if tp_price:
            data['tpPrice'] = str(tp_price)
            data['tpStopType'] = 'LAST'
            data['tpOrderType'] = 'MARKET'
        if sl_price:
            data['slPrice'] = str(sl_price)
            data['slStopType'] = 'LAST'
            data['slOrderType'] = 'MARKET'
        if position_id:
            data['positionId'] = position_id
        return self._post_private('/api/v1/futures/trade/place_order', data)

    def place_limit_order(self, symbol='BTCUSDT', side='BUY', qty=0.001, price=0, trade_side='OPEN'):
        data = {
            'symbol': symbol,
            'side': side,
            'tradeSide': trade_side,
            'orderType': 'LIMIT',
            'qty': str(qty),
            'price': str(price),
            'effect': 'GTC',
        }
        return self._post_private('/api/v1/futures/trade/place_order', data)

    def place_tp_sl(self, symbol='BTCUSDT', side='SELL', qty=0.001, tp_price=None, sl_price=None):
        data = {
            'symbol': symbol,
            'side': side,
            'qty': str(qty),
        }
        if tp_price:
            data['tpPrice'] = str(tp_price)
            data['tpOrderType'] = 'MARKET'
        if sl_price:
            data['slPrice'] = str(sl_price)
            data['slOrderType'] = 'MARKET'
        return self._post_private('/api/v1/futures/tp_sl/place_position_tp_sl_order', data)

    def close_position(self, symbol='BTCUSDT', side='BUY'):
        close_side = 'SELL' if side == 'BUY' else 'BUY'
        return self.place_market_order(symbol, close_side, trade_side='CLOSE', reduce_only=True)

    def get_min_qty(self, symbol='BTCUSDT'):
        """Get minimum order quantity for a symbol"""
        result = self._get_public('/api/v1/futures/market/contracts', {'symbol': symbol})
        if result.get('code') == 0 and result.get('data'):
            for c in result['data']:
                if c.get('symbol') == symbol:
                    return float(c.get('minOrderQty', 0.001))
        return 0.001  # default

    def close_all_positions(self):
        return self._post_private('/api/v1/futures/trade/close_all_position', {})

    def modify_tp_sl(self, symbol='BTCUSDT', position_id=None, tp_price=None, sl_price=None):
        """Modify TP/SL - Bitunix doesn't support direct modification, so we track locally"""
        # Bitunix API doesn't support modifying TP/SL after order is placed
        # We track SL locally and close manually when triggered
        return {'code': -1, 'msg': 'TP/SL modification not supported - using local trailing stop'}

    def get_pending_orders(self, symbol=None):
        params = {}
        if symbol: params['symbol'] = symbol
        return self._get_private('/api/v1/futures/trade/get_pending_orders', params)

    def cancel_all_orders(self, symbol=None):
        data = {}
        if symbol: data['symbol'] = symbol
        return self._post_private('/api/v1/futures/trade/cancel_all_orders', data)

    def get_symbol_info(self, symbol='BTCUSDT'):
        """Get symbol precision and limits"""
        result = self._get_public('/api/v1/futures/market/trading_pairs')
        if result.get('code') == 0 and result.get('data'):
            for pair in result['data']:
                if pair.get('symbol') == symbol:
                    return {
                        'min_qty': float(pair.get('minTradeVolume', 0.001)),
                        'max_qty': float(pair.get('maxMarketOrderVolume', 1000)),
                        'price_precision': int(pair.get('quotePrecision', 2)),
                        'qty_precision': int(pair.get('basePrecision', 3)),
                    }
        # Fallback defaults for BTCUSDT
        return {'min_qty': 0.001, 'max_qty': 1000, 'price_precision': 2, 'qty_precision': 3}


# Quick test
if __name__ == '__main__':
    import sys
    api_key = sys.argv[1] if len(sys.argv) > 1 else ''
    secret_key = sys.argv[2] if len(sys.argv) > 2 else ''
    api = BitunixAPI(api_key, secret_key)

    print("Testing Bitunix API...")

    # Public
    candles = api.get_klines('BTCUSDT', '30m', 5)
    print(f"Klines: {len(candles)} candles")
    for c in candles[-3:]:
        print(f"  {c['timestamp']} O={c['open']} H={c['high']} L={c['low']} C={c['close']}")

    ticker = api.get_ticker('BTCUSDT')
    print(f"Ticker: {ticker}")

    # Private (if keys provided)
    if api_key and secret_key:
        print("\nTesting private endpoints...")
        bal = api.get_balance()
        print(f"Balance: {bal}")

        pos = api.get_positions('BTCUSDT')
        print(f"Positions: {pos}")

        if bal:
            print(f"\n✅ All good! Equity: ${bal['equity']:.2f}")
        else:
            print("\n❌ Balance check failed - check API keys")
    else:
        print("\nNo API keys provided. Run with: python bitunix_api.py API_KEY SECRET_KEY")