#!/usr/bin/env python3
"""
BITUNIX FUTURES TRADING BOT — Template
Copy this file and customize for your strategy.
"""

import json, os, time, hashlib, secrets, math, requests
from datetime import datetime

# ============ CONFIG ============
# Load from config file
with open('/data/crypto-trader/bot_config_final.json') as f:
    CONFIG = json.load(f)

API_KEY = CONFIG['api_key']
API_SECRET = CONFIG['secret_key']
BASE_URL = "https://fapi.bitunix.com"
DRY_RUN = True  # Set False for live trading

# Telegram
TG_TOKEN = "8825978198:AAE9H8mYFv2j5oFZKVuXOQLzxDFW3yZUCys"
TG_CHAT = "8048000483"

# Trading pairs
PAIRS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT']

# State files
STATE_FILE = "/data/crypto-trader/trading_state.json"
LOG_FILE = "/data/crypto-trader/trading_log.json"

# ============ API CLIENT ============
class BitunixFutures:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def _sha256(self, s):
        return hashlib.sha256(s.encode('utf-8')).hexdigest()
    
    def _sign(self, params_str="", body_str=""):
        timestamp = str(int(time.time() * 1000))
        nonce = secrets.token_hex(16)
        
        # Signature uses params WITHOUT equals
        message = nonce + timestamp + self.api_key + params_str + body_str
        digest = self._sha256(message)
        sign = self._sha256(digest + self.api_secret)
        
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
        idx = params_str.rfind("USDT")
        if idx > 0:
            return params_str[:idx] + "=" + params_str[idx:]
        return params_str
    
    def get(self, endpoint, params_str=""):
        headers = self._sign(params_str)
        url_params = self._convert_params(params_str)
        url = f"{BASE_URL}{endpoint}"
        if url_params:
            url += "?" + url_params
        return requests.get(url, headers=headers, timeout=30).json()
    
    def post(self, endpoint, data=None):
        body = json.dumps(data, separators=(',', ':'), sort_keys=True) if data else ""
        headers = self._sign(body_str=body)
        return requests.post(f"{BASE_URL}{endpoint}", data=body, headers=headers, timeout=30).json()
    
    # === PUBLIC (Spot API) ===
    def get_klines(self, symbol, interval="60"):
        url = "https://openapi.bitunix.com/api/spot/v1/market/kline"
        return requests.get(url, params={"symbol": symbol, "interval": interval}, timeout=10).json()
    
    def get_price(self, symbol):
        url = "https://openapi.bitunix.com/api/spot/v1/market/tickers"
        r = requests.get(url, params={"symbol": symbol}, timeout=10).json()
        if r.get('data'):
            for t in r['data']:
                if t.get('symbol') == symbol:
                    return float(t.get('lastPrice', 0))
        return 0
    
    # === FUTURES PRIVATE ===
    def get_account(self, margin_coin="USDT"):
        return self.get("/api/v1/futures/account", f"marginCoin{margin_coin}")
    
    def get_positions(self):
        return self.get("/api/v1/futures/position/current")
    
    def place_market_order(self, symbol, side, size):
        return self.post("/api/v1/futures/order/place_order", {
            "symbol": symbol, "side": side, "type": 2, "size": str(size)
        })
    
    def set_tpsl(self, symbol, tp=None, sl=None, size=None):
        data = {"symbol": symbol}
        if tp:
            data["tpTriggerPrice"] = str(tp)
            data["tpOrderPrice"] = str(tp)
        if sl:
            data["slTriggerPrice"] = str(sl)
            data["slOrderPrice"] = str(sl)
        if size:
            data["size"] = str(size)
        return self.post("/api/v1/futures/tpsl/position_tpsl_order", data)

# ============ INDICATORS ============
def calc_ema(data, period):
    n = len(data); e = [0.0]*n
    if n < 2: return e
    e[0] = data[0]; m = 2.0/(period+1)
    for i in range(1, n): e[i] = data[i]*m + e[i-1]*(1-m)
    return e

def calc_rsi(closes, period=14):
    n = len(closes); r = [50.0]*n
    if n < period+2: return r
    gains, losses = [], []
    for i in range(1, n):
        d = closes[i]-closes[i-1]
        gains.append(max(0,d)); losses.append(max(0,-d))
    ag = sum(gains[:period])/period; al = sum(losses[:period])/period
    if al > 0: r[period] = 100-100/(1+ag/al)
    for i in range(period, len(gains)):
        ag = (ag*(period-1)+gains[i])/period
        al = (al*(period-1)+losses[i])/period
        if al > 0: r[i+1] = 100-100/(1+ag/al)
    return r

def calc_adx(highs, lows, closes, period=14):
    n = len(closes); a = [25.0]*n
    if n < period*2+2: return a
    p_dm, m_dm, trs = [], [], []
    for i in range(1, n):
        up = highs[i]-highs[i-1]; down = lows[i-1]-lows[i]
        p_dm.append(up if up>down and up>0 else 0)
        m_dm.append(down if down>up and down>0 else 0)
        trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
    if len(trs) < period: return a
    atr_s = sum(trs[:period]); pdm_s = sum(p_dm[:period]); ndm_s = sum(m_dm[:period])
    for i in range(period, len(trs)):
        atr_s = atr_s-atr_s/period+trs[i]
        pdm_s = pdm_s-pdm_s/period+p_dm[i]
        ndm_s = ndm_s-ndm_s/period+m_dm[i]
        pdi = 100*pdm_s/atr_s if atr_s>0 else 0
        ndi = 100*ndm_s/atr_s if atr_s>0 else 0
        dx = 100*abs(pdi-ndi)/(pdi+ndi) if (pdi+ndi)>0 else 0
        a[i+1] = dx
    return a

def calc_macd(closes):
    e12 = calc_ema(closes, 12); e26 = calc_ema(closes, 26)
    macd = [e12[i]-e26[i] for i in range(len(closes))]
    sig = calc_ema(macd, 9)
    hist = [macd[i]-sig[i] for i in range(len(closes))]
    return macd, sig, hist

def calc_atr(highs, lows, closes, period=14):
    n = len(closes); atr = [0.0]*n
    if n < 2: return atr
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, n)]
    if len(trs) < period: return atr
    atr[period] = sum(trs[:period])/period
    for i in range(period, len(trs)): atr[i+1] = (atr[i]*(period-1)+trs[i])/period
    return atr

# ============ ANALYSIS ============
def analyze_pair(api, symbol):
    klines_1h = api.get_klines(symbol, "60")
    klines_4h = api.get_klines(symbol, "240")
    
    if not klines_1h.get('data') or len(klines_1h['data']) < 100: return None
    if not klines_4h.get('data') or len(klines_4h['data']) < 50: return None
    
    d1 = klines_1h['data']; d4 = klines_4h['data']
    
    c1 = [float(k['close']) for k in d1]
    h1 = [float(k['high']) for k in d1]
    l1 = [float(k['low']) for k in d1]
    
    c4 = [float(k['close']) for k in d4]
    h4 = [float(k['high']) for k in d4]
    l4 = [float(k['low']) for k in d4]
    
    ema8 = calc_ema(c4, 8)
    ema25 = calc_ema(c4, 25)
    ema100 = calc_ema(c4, 100)
    adx = calc_adx(h4, l4, c4)
    rsi = calc_rsi(c1)
    macd, sig, hist = calc_macd(c1)
    atr = calc_atr(h1, l1, c1)
    
    i4 = len(c4)-1; i1 = len(c1)-1
    price = c1[i1]
    e8, e25, e100 = ema8[i4], ema25[i4], ema100[i4]
    adx_v = adx[i4]
    atr_val = atr[i1] if atr[i1] > 0 else price * 0.01
    atr_pct = atr_val / price
    
    regime = "RANGE"
    if e8 > e25 > e100 and adx_v > 20: regime = "BULL"
    elif e8 < e25 < e100 and adx_v > 20: regime = "BEAR"
    
    signal = None
    if adx_v >= 20:
        if regime == "BULL" and e8 > e25 and rsi[i1] > 45 and hist[i1] > hist[i1-1]:
            signal = "BUY"
        elif regime == "BEAR" and e8 < e25 and rsi[i1] < 55 and hist[i1] < hist[i1-1]:
            signal = "SELL"
        elif regime == "RANGE":
            if rsi[i1] < 30 and hist[i1] > hist[i1-1]:
                signal = "BUY"
            elif rsi[i1] > 70 and hist[i1] < hist[i1-1]:
                signal = "SELL"
    
    tp = sl = None
    if signal == "BUY":
        tp = price * (1 + atr_pct * 2.5)
        sl = price * (1 - atr_pct * 1.5)
    elif signal == "SELL":
        tp = price * (1 - atr_pct * 2.5)
        sl = price * (1 + atr_pct * 1.5)
    
    return {
        'symbol': symbol, 'price': price, 'regime': regime,
        'signal': signal, 'adx': adx_v, 'rsi': rsi[i1],
        'tp': tp, 'sl': sl, 'atr_pct': atr_pct,
    }

# ============ STATE ============
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: return json.load(f)
    return {'balance': 1000.0, 'positions': {}, 'trades': [], 'daily_pnl': 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

# ============ TELEGRAM ============
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        return requests.post(url, json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10).json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

# ============ MAIN ============
def run():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    msg = f"🤖 <b>Bitunix Futures Bot</b>\n⏰ {now}\n{'='*30}\n"
    print(f"\n{'='*60}\n  FUTURES TRADING BOT — {now}\n{'='*60}")
    
    api = BitunixFutures(API_KEY, API_SECRET)
    state = load_state()
    
    # Account
    msg += "\n💰 <b>Account:</b>\n"
    print("\nAccount:")
    try:
        acc = api.get_account()
        if acc.get('code') == 0 and acc.get('data'):
            d = acc['data']
            msg += f"  Available: ${float(d.get('available', 0)):,.2f}\n"
            msg += f"  Margin: ${float(d.get('margin', 0)):,.2f}\n"
            msg += f"  PNL: ${float(d.get('crossUnrealizedPNL', 0)):,.2f}\n"
            print(f"  ✅ Available: ${float(d.get('available', 0)):,.2f}")
        else:
            msg += f"  Error: {acc.get('msg', 'Unknown')}\n"
            print(f"  ❌ {acc.get('msg')}")
    except Exception as e:
        print(f"  Error: {e}")
        msg += f"  Error: {e}\n"
    
    # Positions
    print("\nPositions:")
    try:
        pos = api.get_positions()
        if pos.get('code') == 0 and pos.get('data'):
            msg += f"\n📊 <b>Open Positions:</b>\n"
            for p in pos['data']:
                msg += f"  {p.get('symbol')}: {p.get('side')} ${p.get('available')} PNL: ${p.get('unrealizedPnl', 0)}\n"
                print(f"  ✅ {p.get('symbol')}: {p.get('side')}")
        else:
            msg += f"\n📊 <b>Positions:</b> None\n"
            print(f"  No positions")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Analyze
    msg += f"\n📈 <b>Market Analysis:</b>\n"
    print("\nAnalysis:")
    signals = []
    for pair in PAIRS:
        result = analyze_pair(api, pair)
        if result:
            signals.append(result)
            icon = "🟢" if result['signal'] == 'BUY' else "🔴" if result['signal'] == 'SELL' else "⚪"
            line = f"{icon} {pair}: ${result['price']:,.2f} | {result['regime']} | ADX:{result['adx']:.0f} | RSI:{result['rsi']:.0f}"
            print(f"  {line}")
            msg += f"  {line}\n"
            if result['signal']:
                print(f"    ⚡ {result['signal']}! TP: ${result['tp']:,.2f} SL: ${result['sl']:,.2f}")
                msg += f"  ⚡ <b>{result['signal']}</b> @ ${result['price']:,.2f}\n"
                msg += f"    TP: ${result['tp']:,.2f} | SL: ${result['sl']:,.2f}\n"
    
    # Signals summary
    active = [s for s in signals if s['signal']]
    if active:
        msg += f"\n🎯 <b>{len(active)} Signal(s)!</b>\n"
        for s in active:
            msg += f"  {s['signal']} {s['symbol']} @ ${s['price']:,.2f}\n"
            msg += f"  TP: ${s['tp']:,.2f} | SL: ${s['sl']:,.2f}\n"
            if not DRY_RUN:
                try:
                    side = 1 if s['signal'] == 'BUY' else 2
                    order = api.place_market_order(s['symbol'], side, 1)
                    msg += f"  📤 Order placed: {order.get('msg', 'N/A')}\n"
                    if order.get('code') == 0:
                        tpsl = api.set_tpsl(s['symbol'], s['tp'], s['sl'], 1)
                        msg += f"  📌 TP/SL: {tpsl.get('msg', 'N/A')}\n"
                except Exception as e:
                    msg += f"  ❌ Order error: {e}\n"
            else:
                msg += f"  📝 DRY RUN — No order placed\n"
    else:
        msg += "\n⏸️ No signals — all pairs neutral\n"
    
    msg += f"\n{'='*30}"
    msg += f"\n💰 Balance: ${state['balance']:,.2f}"
    msg += f"\n📊 Trades: {len(state['trades'])}"
    msg += f"\n🔒 Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}"
    
    send_telegram(msg)
    print(f"\n  ✅ Telegram sent!")
    
    save_state(state)
    return signals

if __name__ == "__main__":
    run()