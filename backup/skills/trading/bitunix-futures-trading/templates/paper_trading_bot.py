#!/usr/bin/env python3
"""
BITUNIX FUTURES PAPER TRADING BOT — Template
Complete paper trading implementation with position management, TP/SL tracking, and Telegram reporting.
"""

import json, os, time, hashlib, secrets, math, requests
from datetime import datetime

# ============ CONFIG ============
with open('/data/crypto-trader/bot_config_final.json') as f:
    CONFIG = json.load(f)

API_KEY = CONFIG['api_key']
API_SECRET = CONFIG['secret_key']
BASE_URL = "https://fapi.bitunix.com"
DRY_RUN = True  # Always True for paper trading

# Telegram
TG_TOKEN = "8825978198:AAE9H8mYFv2j5oFZKVuXOQLzxDFW3yZUCys"
TG_CHAT = "8048000483"

# Trading pairs
PAIRS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT']

# State files
STATE_FILE = "/data/crypto-trader/paper_state.json"
LOG_FILE = "/data/crypto-trader/paper_trades.json"
DAILY_LOG_FILE = "/data/crypto-trader/paper_daily.json"

# Risk Parameters
LEVERAGE = 3
RISK_PER_TRADE = 0.015      # 1.5%
MAX_POSITION_PCT = 0.20     # 20% per position
MAX_POSITIONS = 3
TP_ATR_MULT = 2.5
SL_ATR_MULT = 1.5
ADX_THRESHOLD = 20

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
        # Known param patterns
        if params_str.endswith("CoinUSDT"):
            return params_str[:-8] + "=" + params_str[-8:]  # marginCoin=USDT
        elif params_str.endswith("USDT"):
            return params_str[:-4] + "=" + params_str[-4:]   # symbol=BTCUSDT
        return params_str
   
    def get(self, endpoint, params_str=""):
        headers = self._sign(params_str)
        url_params = self._convert_params(params_str)
        url = f"{BASE_URL}{endpoint}"
        if url_params:
            url += '?' + url_params
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
    if e8 > e25 > e100 and adx_v > ADX_THRESHOLD: regime = "BULL"
    elif e8 < e25 < e100 and adx_v > ADX_THRESHOLD: regime = "BEAR"
   
    signal = None
    if adx_v >= ADX_THRESHOLD:
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
        tp = price * (1 + atr_pct * TP_ATR_MULT)
        sl = price * (1 - atr_pct * SL_ATR_MULT)
    elif signal == "SELL":
        tp = price * (1 - atr_pct * TP_ATR_MULT)
        sl = price * (1 + atr_pct * SL_ATR_MULT)
   
    return {
        'symbol': symbol, 'price': price, 'regime': regime,
        'signal': signal, 'adx': adx_v, 'rsi': rsi[i1],
        'tp': tp, 'sl': sl, 'atr_pct': atr_pct,
    }

# ============ STATE ============
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: 
            data = json.load(f)
    else:
        data = {}
    defaults = {
        'equity': 1000.0,
        'positions': {},
        'closed_trades': [],
        'daily_pnl': 0.0,
        'day_start_equity': 1000.0,
        'last_day': datetime.now().date().isoformat()
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    return data

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

def log_trade(trade):
    trades = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f: trades = json.load(f)
    trades.append(trade)
    with open(LOG_FILE, 'w') as f: json.dump(trades, f, indent=2)

def log_daily(summary):
    daily = []
    if os.path.exists(DAILY_LOG_FILE):
        with open(DAILY_LOG_FILE) as f: daily = json.load(f)
    daily.append(summary)
    with open(DAILY_LOG_FILE, 'w') as f: json.dump(daily, f, indent=2)

# ============ PAPER TRADING LOGIC ============
def check_tp_sl(state, api):
    closed = []
    for symbol, pos in list(state['positions'].items()):
        current_price = api.get_price(symbol)
        if current_price == 0: continue
       
        entry = pos['entry']
        side = pos['side']
        tp = pos['tp']
        sl = pos['sl']
        size = pos['size']
       
        hit = None
        exit_price = None
       
        if side == "LONG":
            if current_price >= tp:
                hit = "TP"
                exit_price = tp
            elif current_price <= sl:
                hit = "SL"
                exit_price = sl
        else:  # SHORT
            if current_price <= tp:
                hit = "TP"
                exit_price = tp
            elif current_price >= sl:
                hit = "SL"
                exit_price = sl
       
        if hit:
            if side == "LONG":
                pnl_pct = (exit_price - entry) / entry
            else:
                pnl_pct = (entry - exit_price) / entry
           
            pnl_usd = pnl_pct * entry * size * LEVERAGE
           
            trade = {
                'symbol': symbol,
                'side': side,
                'entry': entry,
                'exit': exit_price,
                'size': size,
                'leverage': LEVERAGE,
                'pnl_pct': round(pnl_pct * 100, 2),
                'pnl_usd': round(pnl_usd, 2),
                'exit_reason': hit,
                'entry_time': pos['entry_time'],
                'exit_time': datetime.now().isoformat(),
                'duration_hours': round((datetime.now() - datetime.fromisoformat(pos['entry_time'])).total_seconds() / 3600, 2)
            }
           
            state['equity'] += pnl_usd
            state['daily_pnl'] += pnl_usd
            state['closed_trades'].append(trade)
            log_trade(trade)
            closed.append((symbol, trade))
            del state['positions'][symbol]
   
    return closed

def open_position(state, api, signal):
    symbol = signal['symbol']
    price = signal['price']
    side = "LONG" if signal['signal'] == "BUY" else "SHORT"
   
    if len(state['positions']) >= MAX_POSITIONS:
        return False, "Max positions reached"
   
    if symbol in state['positions']:
        return False, "Already have position"
   
    same_dir = sum(1 for p in state['positions'].values() 
                   if (p['side'] == "LONG" and side == "LONG") or 
                      (p['side'] == "SHORT" and side == "SHORT"))
    if same_dir >= 2:
        return False, "Correlation limit"
   
    risk_amount = state['equity'] * RISK_PER_TRADE
    sl_distance = abs(price - signal['sl']) / price
    if sl_distance == 0:
        return False, "Invalid SL"
   
    position_value = risk_amount / sl_distance
    max_position_value = state['equity'] * MAX_POSITION_PCT
    position_value = min(position_value, max_position_value)
   
    size = position_value / price
    size = max(size, 0.001)
   
    pos = {
        'symbol': symbol,
        'side': side,
        'entry': price,
        'size': round(size, 6),
        'tp': signal['tp'],
        'sl': signal['sl'],
        'entry_time': datetime.now().isoformat(),
        'leverage': LEVERAGE
    }
   
    state['positions'][symbol] = pos
   
    trade = {
        'symbol': symbol,
        'side': side,
        'entry': price,
        'size': round(size, 6),
        'leverage': LEVERAGE,
        'tp': signal['tp'],
        'sl': signal['sl'],
        'entry_time': pos['entry_time'],
        'status': 'OPEN',
        'type': 'ENTRY'
    }
    log_trade(trade)
   
    return True, pos

def get_portfolio_value(state, api):
    total = state['equity']
    for symbol, pos in state['positions'].items():
        current = api.get_price(symbol)
        if current == 0: continue
        entry = pos['entry']
        side = pos['side']
        size = pos['size']
       
        if side == "LONG":
            unreal_pct = (current - entry) / entry
        else:
            unreal_pct = (entry - current) / entry
       
        unreal_usd = unreal_pct * entry * size * LEVERAGE
        total += unreal_usd
    return total

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
    now = datetime.now()
    today = now.date().isoformat()
   
    state = load_state()
   
    # Daily reset
    if state['last_day'] != today:
        log_daily({
            'date': state['last_day'],
            'start_equity': state['day_start_equity'],
            'end_equity': state['equity'],
            'daily_pnl': state['daily_pnl'],
            'trades': len([t for t in state['closed_trades'] 
                          if t['exit_time'].startswith(state['last_day'])]),
        })
        state['daily_pnl'] = 0.0
        state['day_start_equity'] = state['equity']
        state['last_day'] = today
   
    api = BitunixFutures(API_KEY, API_SECRET)
   
    msg = f"📄 <b>Paper Trading Bot</b>\n⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*30}\n"
    print(f"\n{'='*60}\n  PAPER TRADING — {now.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}")
   
    # Check TP/SL
    closed = check_tp_sl(state, api)
    if closed:
        msg += f"\n🎯 <b>Positions Closed:</b>\n"
        for symbol, trade in closed:
            icon = "🟢" if trade['pnl_usd'] > 0 else "🔴"
            msg += f"  {icon} {trade['symbol']} {trade['side']} {trade['exit_reason']}: ${trade['pnl_usd']:.2f} ({trade['pnl_pct']:.2f}%)\n"
            print(f"  Closed: {trade['symbol']} {trade['side']} {trade['exit_reason']} PnL: ${trade['pnl_usd']:.2f}")
   
    # Account
    acc = api.get_account()
    msg += f"\n💰 <b>Paper Account:</b>\n"
    msg += f"  Equity: ${state['equity']:.2f}\n"
    msg += f"  Daily PnL: ${state['daily_pnl']:.2f}\n"
    msg += f"  Open Positions: {len(state['positions'])}/{MAX_POSITIONS}\n"
   
    portfolio_value = get_portfolio_value(state, api)
    unrealized = portfolio_value - state['equity']
    msg += f"  Unrealized: ${unrealized:.2f}\n"
    msg += f"  Total Value: ${portfolio_value:.2f}\n"
   
    print(f"\nEquity: ${state['equity']:.2f} | Unrealized: ${unrealized:.2f} | Total: ${portfolio_value:.2f}")
   
    # Open positions
    if state['positions']:
        msg += f"\n📊 <b>Open Positions:</b>\n"
        for symbol, pos in state['positions'].items():
            current = api.get_price(symbol)
            if current == 0: continue
            entry = pos['entry']
            side = pos['side']
            size = pos['size']
            tp = pos['tp']
            sl = pos['sl']
           
            if side == "LONG":
                unreal_pct = (current - entry) / entry * 100
            else:
                unreal_pct = (entry - current) / entry * 100
           
            msg += f"  {symbol} {side} @ ${entry:.4f}\n"
            msg += f"    Size: {size:.4f} | Current: ${current:.4f}\n"
            msg += f"    PnL: {unreal_pct:+.2f}% | TP: ${tp:.4f} | SL: ${sl:.4f}\n"
            print(f"  {symbol} {side} @ ${entry:.4f} | PnL: {unreal_pct:+.2f}%")
   
    # Analyze
    msg += f"\n📈 <b>Market Scan:</b>\n"
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
                msg += f"    ⚡ {result['signal']} | TP:${result['tp']:,.2f} SL:${result['sl']:,.2f}\n"
   
    # Execute
    active = [s for s in signals if s['signal']]
    if active:
        msg += f"\n🎯 <b>Executing {len(active)} Signal(s):</b>\n"
        for s in active:
            success, result = open_position(state, api, s)
            if success:
                msg += f"  ✅ {s['signal']} {s['symbol']} @ ${s['price']:.4f}\n"
                msg += f"    Size: {result['size']:.4f} | TP: ${result['tp']:.4f} | SL: ${result['sl']:.4f}\n"
                print(f"  OPENED: {s['signal']} {s['symbol']} @ ${s['price']:.4f}")
            else:
                msg += f"  ⏭️ {s['symbol']} skipped: {result}\n"
                print(f"  Skipped: {s['symbol']} - {result}")
    else:
        msg += "\n⏸️ No new signals\n"
   
    # Stats
    total_trades = len(state['closed_trades'])
    wins = sum(1 for t in state['closed_trades'] if t['pnl_usd'] > 0)
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
   
    msg += f"\n{'='*30}"
    msg += f"\n📊 <b>Stats:</b>"
    msg += f"\n  Total Trades: {total_trades}"
    msg += f"\n  Win Rate: {wr:.1f}%"
    msg += f"\n  Equity: ${state['equity']:.2f}"
    msg += f"\n  Return: {((state['equity']/1000)-1)*100:.1f}%"
   
    send_telegram(msg)
    print(f"\n  ✅ Telegram sent!")
   
    save_state(state)
    return state

if __name__ == "__main__":
    run()