"""
Paper Trading Bot - PRODUCTION FIXED
- Uses unified indicators.py + strategy.py
- Real price updates from Bitunix API
- Unrealized PnL tracking
- Realistic fees (0.04%) and slippage (0.03%)
- Trailing stop with activation threshold
- Single config: bot_config_final.json
"""
import os
import sys
import time
import json
import hashlib
import requests
import logging
import psutil
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import compute_all
from strategy import generate_signal

# ============================================================
# CONFIG
# ============================================================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_config_final.json")

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_trading_state.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_trading_log.txt")
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_trading.lock")

BASE_URL = "https://fapi.bitunix.com"

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def log(msg):
    logger.info(msg)


# ============================================================
# SINGLE INSTANCE LOCK
# ============================================================
def acquire_lock():
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE) as f:
                content = f.read().strip()
            if content:
                parts = content.split("|")
                if len(parts) == 2:
                    pid = int(parts[0])
                    ts = float(parts[1])
                    if time.time() - ts > 300:
                        log(f"Stale lock (PID {pid}, age {time.time()-ts:.0f}s), removing")
                        os.remove(LOCK_FILE)
                    else:
                        try:
                            if psutil.pid_exists(pid):
                                proc = psutil.Process(pid)
                                if "paper_trading" in " ".join(proc.cmdline() or []):
                                    log(f"Another instance running (PID {pid}), exiting")
                                    return False
                            log(f"Dead process (PID {pid}), removing lock")
                            os.remove(LOCK_FILE)
                        except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied):
                            if time.time() - ts > 60:
                                os.remove(LOCK_FILE)
                            else:
                                return False
        with open(LOCK_FILE, "w") as f:
            f.write(f"{os.getpid()}|{time.time()}")
        return True
    except Exception as e:
        log(f"Lock error: {e}")
        return False


def release_lock():
    try:
        os.remove(LOCK_FILE)
    except Exception:
        pass


# ============================================================
# STATE PERSISTENCE
# ============================================================
def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Save state error: {e}")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


# ============================================================
# BITUNIX API (minimal, for candle fetching + balance)
# ============================================================
_session = None


def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=0)
        _session.mount("https://", adapter)
    return _session


def api_get(endpoint, params=None, retries=3, timeout=60):
    session = get_session()
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    last_error = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, params=params, headers=headers, timeout=timeout)
            data = r.json()
            if data.get("code") == 0:
                return data
            last_error = f"API code {data.get('code')}: {data.get('msg', '?')}"
        except requests.exceptions.Timeout:
            last_error = f"Timeout after {timeout}s"
        except Exception as e:
            last_error = str(e)
        if attempt < retries:
            delay = 2 * (2 ** attempt)
            log(f"API retry {attempt+1}/{retries} after {delay}s: {last_error}")
            time.sleep(delay)
    return {"code": -1, "msg": last_error, "data": None}


def get_klines(symbol="BTCUSDT", interval="30m", limit=200):
    return api_get("/api/v1/futures/market/kline", {"symbol": symbol, "interval": interval, "limit": limit})


def get_ticker(symbol="BTCUSDT"):
    result = api_get("/api/v1/futures/market/tickers")
    if result.get("code") == 0 and result.get("data"):
        for t in result["data"]:
            if t.get("symbol") == symbol:
                return {
                    "last": float(t.get("lastPrice", 0)),
                    "high": float(t.get("high", 0)),
                    "low": float(t.get("low", 0)),
                }
    return None


# ============================================================
# PAPER TRADER
# ============================================================
class PaperTrader:
    def __init__(self, cfg):
        self.cfg = cfg
        self.equity = cfg.get("initial_capital", 1000.0)
        self.peak_equity = self.equity
        self.max_dd = 0.0
        self.position = None
        self.consecutive_losses = 0
        self.circuit_pause_until = 0
        self.daily_pnl = 0.0
        self.day_start_equity = self.equity
        self.current_day = None
        self.trade_log = []
        self.monthly_pnl = defaultdict(float)
        self.monthly_trades = defaultdict(int)
        self.last_candle_time = 0
        self.total_trades = 0

        # Fee / slippage (REALISTIC)
        self.slippage_pct = cfg.get("slippage_pct", 0.0003)  # 0.03%
        self.fee_pct = cfg.get("fee_pct", 0.0004)            # 0.04%

        # Risk decay (reduce position after consecutive losses)
        self.risk_decay = cfg.get("risk_decay", 0.5)

        # Restore state
        state = load_state()
        if state:
            self._restore(state)
            log(f"State restored: equity=${self.equity:.2f}, pos={'YES' if self.position else 'NO'}")

    def _get_state(self):
        return {
            "equity": self.equity,
            "peak_equity": self.peak_equity,
            "max_dd": self.max_dd,
            "consecutive_losses": self.consecutive_losses,
            "circuit_pause_until": self.circuit_pause_until,
            "daily_pnl": self.daily_pnl,
            "day_start_equity": self.day_start_equity,
            "current_day": self.current_day,
            "trade_log": self.trade_log[-50:],  # Keep last 50 trades only
            "monthly_pnl": dict(self.monthly_pnl),
            "monthly_trades": dict(self.monthly_trades),
            "last_candle_time": self.last_candle_time,
            "position": self.position,
            "total_trades": self.total_trades,
        }

    def _restore(self, s):
        self.equity = s.get("equity", self.equity)
        self.peak_equity = s.get("peak_equity", self.equity)
        self.max_dd = s.get("max_dd", 0.0)
        self.consecutive_losses = s.get("consecutive_losses", 0)
        self.circuit_pause_until = s.get("circuit_pause_until", 0)
        self.daily_pnl = s.get("daily_pnl", 0.0)
        self.day_start_equity = s.get("day_start_equity", self.equity)
        self.current_day = s.get("current_day")
        self.trade_log = s.get("trade_log", [])
        self.monthly_pnl = defaultdict(float, s.get("monthly_pnl", {}))
        self.monthly_trades = defaultdict(int, s.get("monthly_trades", {}))
        self.last_candle_time = s.get("last_candle_time", 0)
        self.total_trades = s.get("total_trades", 0)
        pos = s.get("position")
        if pos:
            if "trail_price" not in pos:
                pos["trail_price"] = pos.get("entry", 0)
            if "trail_active" not in pos:
                pos["trail_active"] = False
            self.position = pos

    def new_day_check(self, ts):
        day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if self.current_day != day:
            self.current_day = day
            self.day_start_equity = self.equity
            self.daily_pnl = 0.0
            log(f"NEW DAY: {day} | Start Equity: ${self.equity:.2f}")

    def get_daily_dd_pct(self):
        if self.day_start_equity > 0:
            return ((self.day_start_equity - self.equity) / self.day_start_equity) * 100
        return 0.0

    def check_circuit_breaker(self):
        daily_dd = self.get_daily_dd_pct()
        if daily_dd >= self.cfg.get("cb_daily_dd_limit", 3.0):
            if self.circuit_pause_until == 0:
                self.circuit_pause_until = time.time() + self.cfg.get("cb_pause_hours", 1) * 3600
                log(f"CIRCUIT BREAKER! Daily DD: {daily_dd:.2f}% | Paused {self.cfg.get('cb_pause_hours', 1)}h")
            return time.time() < self.circuit_pause_until
        self.circuit_pause_until = 0
        return False

    def calc_sl_tp(self, side, entry_price):
        """Calculate SL/TP prices from config percentages."""
        if side == "BUY":
            sl_pct = self.cfg["buy_sl_pct"]
            tp_pct = self.cfg["buy_tp_pct"]
        else:
            sl_pct = self.cfg["short_sl_pct"]
            tp_pct = self.cfg["short_tp_pct"]
        sl = entry_price * (1 - sl_pct) if side == "BUY" else entry_price * (1 + sl_pct)
        tp = entry_price * (1 + tp_pct) if side == "BUY" else entry_price * (1 - tp_pct)
        return sl, tp

    def calc_qty(self, equity, sl_price, entry_price):
        """Position size: risk_pct of equity / SL distance, with decay."""
        base_risk = self.cfg["risk_pct"]
        # Apply risk decay based on consecutive losses
        if self.consecutive_losses > 0:
            effective_risk = base_risk * (self.risk_decay ** self.consecutive_losses)
        else:
            effective_risk = base_risk
        risk_usd = equity * effective_risk / 100
        sl_dist = abs(entry_price - sl_price)
        if sl_dist <= 0:
            return 0
        qty = risk_usd / sl_dist
        return round(max(0.001, qty), 6)

    def open_position(self, side, signal):
        price = signal["price"]

        # Apply slippage on entry
        if side == "BUY":
            entry_price = price * (1 + self.slippage_pct)
        else:
            entry_price = price * (1 - self.slippage_pct)

        sl, tp = self.calc_sl_tp(side, entry_price)
        qty = self.calc_qty(self.equity, sl, entry_price)
        notional = qty * entry_price

        if notional < self.cfg.get("min_order_usd", 10):
            return

        entry_fee = qty * entry_price * self.fee_pct

        self.position = {
            "side": side,
            "entry": entry_price,
            "sl": sl,
            "tp": tp,
            "qty": qty,
            "entry_time": signal["timestamp"],
            "entry_price": entry_price,
            "trail_price": entry_price,
            "trail_active": False,
            "trade_zone": signal.get("trade_zone", "UNKNOWN"),
            "regime": signal.get("regime", "UNKNOWN"),
            "entry_fee": entry_fee,
            "signal_score": signal.get("buy_score", 0) if side == "BUY" else signal.get("short_score", 0),
        }
        self.consecutive_losses = 0

        sl_pct = self.cfg["buy_sl_pct"] * 100 if side == "BUY" else self.cfg["short_sl_pct"] * 100
        tp_pct = self.cfg["buy_tp_pct"] * 100 if side == "BUY" else self.cfg["short_tp_pct"] * 100
        log(
            f"OPEN {side} | Entry: ${entry_price:.2f} | SL: ${sl:.2f} (-{sl_pct:.2f}%) "
            f"| TP: ${tp:.2f} (+{tp_pct:.2f}%) | Qty: {qty:.6f} | "
            f"Zone: {signal.get('trade_zone', '?')} | Regime: {signal.get('regime', '?')} | "
            f"Score: {self.position['signal_score']}"
        )

    def manage_position(self, high, low, close, ts):
        """Check SL/TP/Trail and close if needed."""
        if not self.position:
            return

        side = self.position["side"]
        entry = self.position["entry"]
        sl = self.position["sl"]
        tp = self.position["tp"]
        trail_pct = self.cfg.get("trail_pct", 2.5) / 100
        trail_activation_pct = self.cfg.get("trail_activation_pct", 0.015)

        exit_price = None
        reason = None

        if side == "BUY":
            # Check SL
            if low <= sl:
                exit_price = sl
                reason = "SL"
            # Check TP
            elif high >= tp:
                exit_price = tp
                reason = "TP"
            else:
                # Trail activation
                profit_pct = (high - entry) / entry
                if not self.position.get("trail_active") and profit_pct >= trail_activation_pct:
                    self.position["trail_active"] = True
                    self.position["trail_price"] = high * (1 - trail_pct)
                    log(f"TRAIL ACTIVATED | High: ${high:.2f} | Trail: ${self.position['trail_price']:.2f}")

                if self.position.get("trail_active"):
                    new_trail = max(self.position["trail_price"], high * (1 - trail_pct))
                    if new_trail > self.position["trail_price"]:
                        self.position["trail_price"] = new_trail
                    if low <= self.position["trail_price"]:
                        exit_price = self.position["trail_price"]
                        reason = "TRAIL"

        else:  # SELL
            if high >= sl:
                exit_price = sl
                reason = "SL"
            elif low <= tp:
                exit_price = tp
                reason = "TP"
            else:
                profit_pct = (entry - low) / entry
                if not self.position.get("trail_active") and profit_pct >= trail_activation_pct:
                    self.position["trail_active"] = True
                    self.position["trail_price"] = low * (1 + trail_pct)
                    log(f"TRAIL ACTIVATED | Low: ${low:.2f} | Trail: ${self.position['trail_price']:.2f}")

                if self.position.get("trail_active"):
                    new_trail = min(self.position["trail_price"], low * (1 + trail_pct))
                    if new_trail < self.position["trail_price"]:
                        self.position["trail_price"] = new_trail
                    if high >= self.position["trail_price"]:
                        exit_price = self.position["trail_price"]
                        reason = "TRAIL"

        # Max hold check
        if exit_price is None:
            hold_hours = (ts - self.position["entry_time"]) / 3600
            if hold_hours >= self.cfg.get("max_hold", 48):
                exit_price = close
                reason = "MAX_HOLD"

        if exit_price:
            self._close_position(exit_price, reason, ts)

    def _close_position(self, exit_price, reason, ts):
        """Close position and record trade."""
        side = self.position["side"]
        entry = self.position["entry"]
        qty = self.position["qty"]
        entry_fee = self.position.get("entry_fee", 0)

        # Apply slippage on exit
        if side == "BUY":
            exit_price *= (1 - self.slippage_pct)
        else:
            exit_price *= (1 + self.slippage_pct)

        # PnL
        if side == "BUY":
            gross_pnl = (exit_price - entry) * qty
        else:
            gross_pnl = (entry - exit_price) * qty

        exit_fee = qty * exit_price * self.fee_pct
        total_fees = entry_fee + exit_fee
        net_pnl = gross_pnl - total_fees
        pnl_pct_balance = (net_pnl / self.equity * 100) if self.equity > 0 else 0

        self.equity += net_pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        dd = (self.peak_equity - self.equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        if dd > self.max_dd:
            self.max_dd = dd

        self.daily_pnl += net_pnl
        self.total_trades += 1

        month_key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")
        self.monthly_pnl[month_key] += pnl_pct_balance
        self.monthly_trades[month_key] += 1

        if net_pnl > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        hold_hours = (ts - self.position["entry_time"]) / 3600
        trade = {
            "side": side,
            "entry": entry,
            "exit": exit_price,
            "qty": qty,
            "gross_pnl": gross_pnl,
            "fee": total_fees,
            "net_pnl": net_pnl,
            "pnl_pct": pnl_pct_balance,
            "reason": reason,
            "hold_hours": hold_hours,
            "entry_time": self.position["entry_time"],
            "exit_time": ts,
            "trade_zone": self.position.get("trade_zone", "?"),
            "regime": self.position.get("regime", "?"),
            "score": self.position.get("signal_score", 0),
        }
        self.trade_log.append(trade)

        icon = "[WIN]" if net_pnl > 0 else "[LOSS]"
        log(
            f"{icon} CLOSED ({reason}) {side} | Exit: ${exit_price:.2f} | "
            f"PnL: ${net_pnl:+.2f} ({pnl_pct_balance:+.2f}%) | "
            f"Hold: {hold_hours:.1f}h | Fees: ${total_fees:.2f} | "
            f"Equity: ${self.equity:.2f} | Trades: {self.total_trades}"
        )

        self.position = None
        save_state(self._get_state())

    def get_unrealized_pnl(self, current_price):
        """Calculate unrealized PnL for open position."""
        if not self.position:
            return 0.0
        entry = self.position["entry"]
        qty = self.position["qty"]
        if self.position["side"] == "BUY":
            return (current_price - entry) * qty
        else:
            return (entry - current_price) * qty


# ============================================================
# MAIN LOOP
# ============================================================
def run_paper_trading(days=5):
    cfg = load_config()
    log("=" * 70)
    log(f"PAPER TRADING STARTED — Duration: {days} days | Config: bot_config_final.json")
    log(f"  Symbol: {cfg['symbol']} x{cfg['leverage']} | SL: {cfg['buy_sl_pct']*100:.2f}%/{cfg['short_sl_pct']*100:.2f}%")
    log(f"  TP: {cfg['buy_tp_pct']*100:.2f}%/{cfg['short_tp_pct']*100:.2f}% | Trail: {cfg.get('trail_pct', 3.5)}%")
    log(f"  Fee: {cfg.get('fee_pct', 0.0004)*100:.2f}% | Slippage: {cfg.get('slippage_pct', 0.0003)*100:.2f}%")
    log(f"  Min Score: {cfg['min_score']} | Risk: {cfg['risk_pct']}% | Circuit DD: {cfg.get('cb_daily_dd_limit', 3)}%")
    log(f"  Risk Decay: {cfg.get('risk_decay', 0.5)}x | CB Pause: {cfg.get('cb_pause_hours', 96)}h | MaxHold: {cfg.get('max_hold', 72)}")
    log(f"  HTF: 1H + 4H EMA confirmation")
    log("=" * 70)

    if not acquire_lock():
        log("Could not acquire lock, exiting")
        return

    try:
        trader = PaperTrader(cfg)

        # Fetch initial candle history (need 200+ for EMA200)
        log("Fetching initial candle history (500 candles)...")
        kl = get_klines(limit=500)
        if kl.get("code") != 0 or not kl.get("data"):
            log(f"ERROR fetching candles: {kl}")
            return

        candles = []
        for d in kl["data"]:
            candles.append({
                "timestamp": int(d["time"]) // 1000,
                "open": float(d["open"]),
                "high": float(d["high"]),
                "low": float(d["low"]),
                "close": float(d["close"]),
                "volume": float(d.get("quoteVol", 0)),
            })
        candles.sort(key=lambda x: x["timestamp"])
        trader.last_candle_time = candles[-1]["timestamp"]
        log(f"Loaded {len(candles)} candles. Latest: {datetime.fromtimestamp(candles[-1]['timestamp'], tz=timezone.utc)}")

        # Fetch HTF candles for confirmation (1h and 4h)
        log("Fetching 1H/4H candles for HTF confirmation...")
        htf_1h_ind = None
        htf_4h_ind = None
        try:
            kl_1h = get_klines(interval="1h", limit=200)
            if kl_1h.get("code") == 0 and kl_1h.get("data"):
                htf_candles = [{"timestamp": int(d["time"])//1000, "open": float(d["open"]),
                               "high": float(d["high"]), "low": float(d["low"]),
                               "close": float(d["close"]), "volume": float(d.get("quoteVol",0))}
                              for d in kl_1h["data"]]
                htf_candles.sort(key=lambda x: x["timestamp"])
                htf_1h_ind = compute_all(htf_candles, cfg)
                log(f"  1H: {len(htf_candles)} candles loaded")

            kl_4h = get_klines(interval="4h", limit=200)
            if kl_4h.get("code") == 0 and kl_4h.get("data"):
                htf_candles = [{"timestamp": int(d["time"])//1000, "open": float(d["open"]),
                               "high": float(d["high"]), "low": float(d["low"]),
                               "close": float(d["close"]), "volume": float(d.get("quoteVol",0))}
                              for d in kl_4h["data"]]
                htf_candles.sort(key=lambda x: x["timestamp"])
                htf_4h_ind = compute_all(htf_candles, cfg)
                log(f"  4H: {len(htf_candles)} candles loaded")
        except Exception as e:
            log(f"  HTF fetch error: {e} (continuing without HTF)")

        end_time = time.time() + days * 24 * 3600
        cycle = 0

        while time.time() < end_time:
            cycle += 1
            try:
                # Fetch latest candles from API
                kl = get_klines(limit=10)
                if kl.get("code") != 0 or not kl.get("data"):
                    log(f"API Error: {kl.get('msg', 'No data')}")
                    time.sleep(60)
                    continue

                # Get current price from ticker
                ticker = get_ticker(cfg["symbol"])
                current_price = ticker["last"] if ticker else None

                # Process each new candle
                for d in kl["data"]:
                    ts = int(d["time"]) // 1000
                    if ts <= trader.last_candle_time:
                        continue  # Skip old candles

                    c = {
                        "timestamp": ts,
                        "open": float(d["open"]),
                        "high": float(d["high"]),
                        "low": float(d["low"]),
                        "close": float(d["close"]),
                        "volume": float(d.get("quoteVol", 0)),
                    }

                    # Add to history
                    candles.append(c)
                    trader.last_candle_time = ts

                    # Trim to 1000 candles max
                    if len(candles) > 1000:
                        candles = candles[-1000:]

                    # Day check
                    trader.new_day_check(ts)

                    # Manage existing position (check SL/TP/Trail against candle H/L)
                    if trader.position:
                        trader.manage_position(c["high"], c["low"], c["close"], ts)

                    # Check for new signals (only if no position and no circuit breaker)
                    if not trader.position and not trader.check_circuit_breaker():
                        if len(candles) >= 200:
                            ind = compute_all(candles, cfg)
                            signal = generate_signal(ind, len(candles) - 1, cfg, htf_1h_ind, htf_4h_ind)
                            if signal:
                                log(
                                    f"SIGNAL: {signal['side']} | Score: {signal.get('buy_score',0)}/{signal.get('short_score',0)} | "
                                    f"Regime: {signal['regime']} | RSI: {signal['rsi']:.1f} | ADX: {signal['adx']:.1f} | "
                                    f"Price: ${signal['price']:.2f} | Zone: {signal.get('trade_zone','?')}"
                                )
                                if signal["side"] == "BUY":
                                    trader.open_position("BUY", signal)
                                else:
                                    trader.open_position("SELL", signal)

                # After processing candles, show status
                unrealized = trader.get_unrealized_pnl(current_price) if current_price and trader.position else 0
                total_equity = trader.equity + unrealized
                dd = (trader.peak_equity - total_equity) / trader.peak_equity * 100 if trader.peak_equity > 0 else 0
                daily_dd = trader.get_daily_dd_pct()
                cb = "PAUSED" if trader.circuit_pause_until > time.time() else "OK"

                pos_str = "None"
                if trader.position and current_price:
                    pnl_unreal = trader.get_unrealized_pnl(current_price)
                    pos_str = (
                        f"{trader.position['side']}@${trader.position['entry']:.2f} "
                        f"SL:${trader.position['sl']:.2f} TP:${trader.position['tp']:.2f} "
                        f"uPnL:${pnl_unreal:+.2f}"
                    )

                log(
                    f"Cycle {cycle} | Price: ${current_price:.2f} | "
                    f"Equity: ${total_equity:.2f} (realized: ${trader.equity:.2f} + unreal: ${unrealized:+.2f}) | "
                    f"DD: {dd:.2f}% | MaxDD: {trader.max_dd:.2f}% | DailyDD: {daily_dd:.2f}% | "
                    f"Trades: {trader.total_trades} | CB: {cb} | POS: {pos_str}"
                )

                # Save state periodically
                if cycle % 5 == 0:
                    save_state(trader._get_state())

                # Sleep 25 seconds (candles update every 30m, but we poll frequently for SL/TP)
                time.sleep(25)

            except KeyboardInterrupt:
                log("STOPPED BY USER")
                break
            except Exception as e:
                log(f"ERROR in main loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(30)

    finally:
        release_lock()
        _print_report(trader)


def _print_report(trader):
    log("=" * 70)
    log("PAPER TRADING FINAL REPORT")
    log("=" * 70)
    log(f"Total Trades: {trader.total_trades}")
    log(f"Final Equity: ${trader.equity:.2f}")
    total_pnl = trader.equity - 1000
    log(f"Total PnL: ${total_pnl:+.2f} ({total_pnl/10:.2f}%)")
    log(f"Max Drawdown: {trader.max_dd:.2f}%")

    if trader.trade_log:
        wins = sum(1 for t in trader.trade_log if t["net_pnl"] > 0)
        losses = len(trader.trade_log) - wins
        wr = wins / len(trader.trade_log) * 100
        gross_profit = sum(t["net_pnl"] for t in trader.trade_log if t["net_pnl"] > 0)
        gross_loss = abs(sum(t["net_pnl"] for t in trader.trade_log if t["net_pnl"] <= 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        avg_hold = sum(t["hold_hours"] for t in trader.trade_log) / len(trader.trade_log)
        total_fees = sum(t["fee"] for t in trader.trade_log)

        log(f"Win Rate: {wr:.1f}% ({wins}W / {losses}L)")
        log(f"Profit Factor: {pf:.2f}")
        log(f"Avg Hold: {avg_hold:.1f}h")
        log(f"Total Fees: ${total_fees:.2f}")

        # Monthly breakdown
        if trader.monthly_pnl:
            log("\n--- Monthly PnL% ---")
            for m in sorted(trader.monthly_pnl.keys()):
                t = trader.monthly_trades[m]
                log(f"  {m}: {trader.monthly_pnl[m]:+.2f}% ({t} trades)")

        # Zone breakdown
        zone_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0})
        for t in trader.trade_log:
            z = t.get("trade_zone", "?")
            zone_stats[z]["trades"] += 1
            if t["net_pnl"] > 0:
                zone_stats[z]["wins"] += 1
            zone_stats[z]["pnl"] += t["pnl_pct"]

        log("\n--- Trade Zone Breakdown ---")
        for zone, stats in sorted(zone_stats.items()):
            wr_z = stats["wins"] / stats["trades"] * 100 if stats["trades"] > 0 else 0
            avg = stats["pnl"] / stats["trades"] if stats["trades"] > 0 else 0
            log(f"  {zone}: {stats['trades']} trades | WR={wr_z:.1f}% | Avg PnL={avg:+.2f}%")

        # Exit reason breakdown
        reason_stats = defaultdict(lambda: {"count": 0, "pnl": 0.0})
        for t in trader.trade_log:
            reason_stats[t["reason"]]["count"] += 1
            reason_stats[t["reason"]]["pnl"] += t["net_pnl"]
        log("\n--- Exit Reasons ---")
        for reason, stats in sorted(reason_stats.items()):
            log(f"  {reason}: {stats['count']} trades | PnL: ${stats['pnl']:+.2f}")

    log("=" * 70)


if __name__ == "__main__":
    run_paper_trading(5)
