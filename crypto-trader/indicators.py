"""
Technical Indicators - Single Source of Truth
All indicators used by the trading bot.
v2: Added VWAP, OBV, Keltner Channels, Supertrend, ATR-based SL/TP
"""
import math


def calc_rsi(closes, period=8):
    """Relative Strength Index using Wilder's smoothing."""
    n = len(closes)
    rsi = [50.0] * n
    if n < period + 2:
        return rsi
    gains, losses = [], []
    for i in range(1, n):
        d = closes[i] - closes[i - 1]
        gains.append(max(0, d))
        losses.append(max(0, -d))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    if al > 0:
        rsi[period] = 100 - 100 / (1 + ag / al)
    elif ag > 0:
        rsi[period] = 100
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        if al > 0:
            rsi[i + 1] = 100 - 100 / (1 + ag / al)
        elif ag > 0:
            rsi[i + 1] = 100
    return rsi


def calc_ema(data, period):
    """Exponential Moving Average."""
    n = len(data)
    ema = [0.0] * n
    if n == 0:
        return ema
    ema[0] = data[0]
    mult = 2.0 / (period + 1)
    for i in range(1, n):
        ema[i] = data[i] * mult + ema[i - 1] * (1 - mult)
    return ema


def calc_sma(data, period):
    """Simple Moving Average."""
    n = len(data)
    sma = [0.0] * n
    for i in range(period - 1, n):
        sma[i] = sum(data[i - period + 1 : i + 1]) / period
    return sma


def calc_atr(highs, lows, closes, period=14):
    """Average True Range."""
    n = len(closes)
    atr = [0.0] * n
    if n < period + 2:
        return atr
    trs = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    atr[period] = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr[i + 1] = (atr[i] * (period - 1) + trs[i]) / period
    return atr


def calc_adx(highs, lows, closes, period=14):
    """Average Directional Index."""
    n = len(closes)
    adx = [25.0] * n
    if n < period * 2 + 2:
        return adx
    plus_dm, minus_dm, trs = [], [], []
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    atr_s = sum(trs[:period])
    pdm_s = sum(plus_dm[:period])
    ndm_s = sum(minus_dm[:period])
    for i in range(period, len(trs)):
        atr_s = atr_s - atr_s / period + trs[i]
        pdm_s = pdm_s - pdm_s / period + plus_dm[i]
        ndm_s = ndm_s - ndm_s / period + minus_dm[i]
        pdi = 100 * pdm_s / atr_s if atr_s > 0 else 0
        ndi = 100 * ndm_s / atr_s if atr_s > 0 else 0
        dx = 100 * abs(pdi - ndi) / (pdi + ndi) if (pdi + ndi) > 0 else 0
        adx[i + 1] = dx
    return adx


def calc_bb(closes, period=20, std_mult=2.0):
    """Bollinger Bands: upper, lower."""
    n = len(closes)
    upper = list(closes)
    lower = list(closes)
    for i in range(period - 1, n):
        w = closes[i - period + 1 : i + 1]
        m = sum(w) / period
        s = math.sqrt(sum((x - m) ** 2 for x in w) / period)
        upper[i] = m + std_mult * s
        lower[i] = m - std_mult * s
    return upper, lower


def calc_stoch_rsi(closes, rsi_period=8, stoch_period=14):
    """Stochastic RSI."""
    rsi = calc_rsi(closes, rsi_period)
    n = len(rsi)
    stoch = [50.0] * n
    for i in range(stoch_period, n):
        w = rsi[i - stoch_period + 1 : i + 1]
        mn, mx = min(w), max(w)
        stoch[i] = ((rsi[i] - mn) / (mx - mn)) * 100 if mx > mn else 50
    return calc_ema(stoch, 3)


def calc_williams(highs, lows, closes, period=14):
    """Williams %R."""
    n = len(closes)
    wr = [-50.0] * n
    for i in range(period - 1, n):
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        if hh > ll:
            wr[i] = -100 * (hh - closes[i]) / (hh - ll)
    return wr


def calc_mfi(highs, lows, closes, volumes, period=14):
    """Money Flow Index."""
    n = len(closes)
    mfi = [50.0] * n
    tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(n)]
    mf = [tp[i] * volumes[i] for i in range(n)]
    for i in range(period, n):
        pos, neg = 0, 0
        for j in range(i - period + 1, i + 1):
            if j > i - period + 1:
                if tp[j] > tp[j - 1]:
                    pos += mf[j]
                else:
                    neg += mf[j]
        if neg > 0:
            mfi[i] = 100 - 100 / (1 + pos / neg)
    return mfi


def calc_macd(closes, fast=12, slow=26, signal_period=9):
    """MACD: line, signal, histogram."""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    macd_signal = calc_ema(macd_line, signal_period)
    macd_hist = [m - s for m, s in zip(macd_line, macd_signal)]
    return macd_line, macd_signal, macd_hist


# ============================================================
# NEW INDICATORS v2
# ============================================================

def calc_vwap(highs, lows, closes, volumes):
    """
    Volume Weighted Average Price.
    Institutional benchmark price — acts as dynamic support/resistance.
    """
    n = len(closes)
    vwap = [0.0] * n
    cum_tp_vol = 0.0
    cum_vol = 0.0
    for i in range(n):
        tp = (highs[i] + lows[i] + closes[i]) / 3
        cum_tp_vol += tp * volumes[i]
        cum_vol += volumes[i]
        vwap[i] = cum_tp_vol / cum_vol if cum_vol > 0 else closes[i]
    return vwap


def calc_obv(closes, volumes):
    """
    On-Balance Volume.
    Measures cumulative volume flow — confirms price moves.
    """
    n = len(closes)
    obv = [0.0] * n
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            obv[i] = obv[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            obv[i] = obv[i - 1] - volumes[i]
        else:
            obv[i] = obv[i - 1]
    return obv


def calc_obv_ema(obv, period=20):
    """OBV EMA — smoothed OBV for signal generation."""
    return calc_ema(obv, period)


def calc_keltner(highs, lows, closes, ema_period=20, atr_period=10, mult=1.5):
    """
    Keltner Channels — ATR-based bands (more robust than BB in trends).
    Returns: upper, middle, lower
    """
    middle = calc_ema(closes, ema_period)
    atr = calc_atr(highs, lows, closes, atr_period)
    n = len(closes)
    upper = [0.0] * n
    lower = [0.0] * n
    for i in range(n):
        upper[i] = middle[i] + mult * atr[i]
        lower[i] = middle[i] - mult * atr[i]
    return upper, middle, lower


def calc_supertrend(highs, lows, closes, period=10, multiplier=3.0):
    """
    Supertrend indicator — ATR-based trend line.
    Returns: trend values, direction (1=up, -1=down)
    """
    n = len(closes)
    atr = calc_atr(highs, lows, closes, period)
    st = [0.0] * n
    direction = [1] * n  # 1=up, -1=down

    upper_band = [0.0] * n
    lower_band = [0.0] * n

    for i in range(n):
        hl2 = (highs[i] + lows[i]) / 2
        upper_band[i] = hl2 + multiplier * atr[i]
        lower_band[i] = hl2 - multiplier * atr[i]

    # Smooth bands
    for i in range(1, n):
        if lower_band[i] > lower_band[i - 1] or closes[i - 1] < lower_band[i - 1]:
            pass
        else:
            lower_band[i] = lower_band[i - 1]

        if upper_band[i] < upper_band[i - 1] or closes[i - 1] > upper_band[i - 1]:
            pass
        else:
            upper_band[i] = upper_band[i - 1]

    # Determine direction
    for i in range(1, n):
        if direction[i - 1] == 1:  # was uptrend
            if closes[i] < lower_band[i]:
                direction[i] = -1
                st[i] = upper_band[i]
            else:
                direction[i] = 1
                st[i] = lower_band[i]
        else:  # was downtrend
            if closes[i] > upper_band[i]:
                direction[i] = 1
                st[i] = lower_band[i]
            else:
                direction[i] = -1
                st[i] = upper_band[i]

    return st, direction


def calc_atr_sl_tp(side, entry_price, atr, cfg):
    """
    ATR-based dynamic SL/TP calculation.
    More professional than fixed percentage.
    """
    atr_mult = cfg.get("atr_sl_mult", 1.5)
    rr_ratio = cfg.get("risk_reward", 2.5)

    if atr > 0:
        sl_dist = atr * atr_mult
        tp_dist = sl_dist * rr_ratio

        # Safety bounds
        max_sl_pct = cfg.get("max_sl_pct", 0.03)  # 3% max SL
        min_sl_pct = cfg.get("min_sl_pct", 0.003)  # 0.3% min SL
        max_tp_pct = cfg.get("max_tp_pct", 0.06)   # 6% max TP
        min_tp_pct = cfg.get("min_tp_pct", 0.005)  # 0.5% min TP

        sl_pct = max(min_sl_pct, min(max_sl_pct, sl_dist / entry_price))
        tp_pct = max(min_tp_pct, min(max_tp_pct, tp_dist / entry_price))

        if side == "BUY":
            sl = entry_price * (1 - sl_pct)
            tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + sl_pct)
            tp = entry_price * (1 - tp_pct)

        return sl, tp
    else:
        # Fallback to fixed
        if side == "BUY":
            return entry_price * 0.995, entry_price * 1.035
        else:
            return entry_price * 1.005, entry_price * 0.965


def compute_all(candles, cfg=None):
    """
    Compute ALL indicators from candle data.
    Returns dict with all indicator arrays.
    """
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]
    n = len(candles)

    rsi_period = cfg.get("rsi_period", 8) if cfg else 8

    # Original indicators
    rsi = calc_rsi(closes, rsi_period)
    ema_fast = calc_ema(closes, cfg.get("ema_fast", 12) if cfg else 12)
    ema_mid = calc_ema(closes, cfg.get("ema_mid", 21) if cfg else 21)
    ema_slow = calc_ema(closes, cfg.get("ema_slow", 40) if cfg else 40)
    ema50 = calc_ema(closes, 50)
    ema200 = calc_ema(closes, 200)
    atr = calc_atr(highs, lows, closes, 14)
    adx = calc_adx(highs, lows, closes, 14)
    bb_upper, bb_lower = calc_bb(closes, 20, 2.0)
    stoch_rsi = calc_stoch_rsi(closes, rsi_period, 14)
    willr = calc_williams(highs, lows, closes, 14)
    mfi = calc_mfi(highs, lows, closes, volumes, 14)
    macd_line, macd_signal, macd_hist = calc_macd(closes)
    vol_sma = calc_sma(volumes, 20)
    atr_sma = calc_ema(atr, 20)

    # NEW v2 indicators
    vwap = calc_vwap(highs, lows, closes, volumes)
    obv = calc_obv(closes, volumes)
    obv_ema = calc_obv_ema(obv, 20)
    keltner_upper, keltner_mid, keltner_lower = calc_keltner(highs, lows, closes)
    supertrend, st_direction = calc_supertrend(highs, lows, closes)

    return {
        # Original
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_mid": ema_mid,
        "ema_slow": ema_slow,
        "ema50": ema50,
        "ema200": ema200,
        "atr": atr,
        "adx": adx,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "stoch_rsi": stoch_rsi,
        "willr": willr,
        "mfi": mfi,
        "macd_hist": macd_hist,
        "vol_sma": vol_sma,
        "atr_sma": atr_sma,
        "timestamps": [c["timestamp"] for c in candles],
        # NEW v2
        "vwap": vwap,
        "obv": obv,
        "obv_ema": obv_ema,
        "keltner_upper": keltner_upper,
        "keltner_mid": keltner_mid,
        "keltner_lower": keltner_lower,
        "supertrend": supertrend,
        "st_direction": st_direction,
    }
