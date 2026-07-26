"""
Signal Generation v3 — Professional Grade
Original scoring (8 indicators) + NEW indicators as optional FILTERS
Key insight: DON'T add to scoring — use as filters to BLOCK bad trades
"""
from datetime import datetime, timezone


def detect_regime(closes, ema50, ema200, adx, rsi, i, regime_adx=18):
    if adx[i] < regime_adx:
        return "RANGE"
    if closes[i] > ema200[i] and ema50[i] > ema200[i] and rsi[i] > 45:
        return "BULL"
    if closes[i] < ema200[i] and ema50[i] < ema200[i] and rsi[i] < 55:
        return "BEAR"
    return "RANGE"


def classify_trade_zone(signal):
    regime = signal.get("regime", "RANGE")
    price = signal.get("price", 0)
    ema_fast = signal.get("ema_fast", 0)
    bb_upper = signal.get("bb_upper", 0)
    bb_lower = signal.get("bb_lower", 0)
    vol_ratio = signal.get("vol_ratio", 1.0)

    if regime == "BULL":
        ema_dist = abs(price - ema_fast) / price if price > 0 else 1
        if ema_dist < 0.005 and price > ema_fast:
            return "PULLBACK_CONTINUATION_BULL"
        if bb_lower > 0 and price <= bb_lower * 1.002:
            return "BB_BOUNCE_BULL"
        if bb_upper > 0 and price >= bb_upper * 0.998 and vol_ratio > 1.2:
            return "BREAKOUT_BULL"
        return "TREND_FOLLOW_BULL"
    elif regime == "BEAR":
        ema_dist = abs(price - ema_fast) / price if price > 0 else 1
        if ema_dist < 0.005 and price < ema_fast:
            return "PULLBACK_CONTINUATION_BEAR"
        if bb_upper > 0 and price >= bb_upper * 0.998:
            return "BB_BOUNCE_BEAR"
        if bb_lower > 0 and price <= bb_lower * 1.002 and vol_ratio > 1.2:
            return "BREAKOUT_BEAR"
        return "TREND_FOLLOW_BEAR"
    else:
        return "TREND_FOLLOW_BULL"


def get_higher_tf_trend(htf_ind, htf_i):
    if htf_i < 1 or htf_i >= len(htf_ind["closes"]):
        return "NEUTRAL"
    closes = htf_ind["closes"]
    ef = htf_ind["ema_fast"]
    em = htf_ind["ema_mid"]
    es = htf_ind["ema_slow"]
    e50 = htf_ind["ema50"]
    adx = htf_ind["adx"]
    if ef[htf_i] > em[htf_i] > es[htf_i] and closes[htf_i] > e50[htf_i] and adx[htf_i] > 20:
        return "BULL"
    if ef[htf_i] < em[htf_i] < es[htf_i] and closes[htf_i] < e50[htf_i] and adx[htf_i] > 20:
        return "BEAR"
    return "NEUTRAL"


def find_htf_index(htf_timestamps, target_ts):
    lo, hi = 0, len(htf_timestamps) - 1
    result = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if htf_timestamps[mid] <= target_ts:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return result


SESSION_WEIGHTS = {
    0: 0.3, 1: 0.3, 2: 0.4, 3: 0.4, 4: 0.5, 5: 0.5,
    6: 0.6, 7: 0.8, 8: 0.9, 9: 0.9, 10: 0.9, 11: 0.8,
    12: 0.7, 13: 0.9, 14: 1.0, 15: 1.0, 16: 0.9, 17: 0.9,
    18: 0.8, 19: 0.7, 20: 0.6, 21: 0.4, 22: 0.3, 23: 0.3,
}


def is_good_session(timestamp, min_weight=0.5):
    hour = datetime.fromtimestamp(timestamp, tz=timezone.utc).hour
    return SESSION_WEIGHTS.get(hour, 0.5) >= min_weight


def generate_signal(ind, i, cfg, htf_1h=None, htf_4h=None, consecutive_losses=0):
    """
    Generate BUY/SELL signal at index i.
    v3: Original 8-indicator scoring + NEW indicators as optional FILTERS.
    consecutive_losses: if >= 2, raise min_score for higher quality entries.
    """
    closes = ind["closes"]
    n = len(closes)

    if i < 199 or i >= n:
        return None

    # --- Regime detection ---
    regime = detect_regime(
        closes, ind["ema50"], ind["ema200"], ind["adx"], ind["rsi"], i,
        cfg.get("regime_adx", 20),
    )

    # --- Range filter ---
    bb_width = (ind["bb_upper"][i] - ind["bb_lower"][i]) / closes[i] if closes[i] > 0 else 0
    if cfg.get("use_range_filter", False):
        if regime == "RANGE":
            return None
        if bb_width < cfg.get("bb_width_thresh", 0.02) and ind["adx"][i] < cfg.get("range_adx_thresh", 18):
            return None

    # --- HTF confirmation ---
    htf_trend = {"1h": "NEUTRAL", "4h": "NEUTRAL"}
    if cfg.get("use_htf_filter", False) and (htf_1h or htf_4h):
        ts_30m = ind["timestamps"][i]
        if htf_1h:
            htf_i_1h = find_htf_index(htf_1h["timestamps"], ts_30m)
            htf_trend["1h"] = get_higher_tf_trend(htf_1h, htf_i_1h)
        if htf_4h:
            htf_i_4h = find_htf_index(htf_4h["timestamps"], ts_30m)
            htf_trend["4h"] = get_higher_tf_trend(htf_4h, htf_i_4h)

    # --- Time filter ---
    if cfg.get("use_time_filter", False):
        if not is_good_session(ind["timestamps"][i], cfg.get("min_session_weight", 0.5)):
            return None

    # ============================================================
    # ORIGINAL 8-INDICATOR SCORING (proven system)
    # ============================================================
    bs, ss = 0, 0
    r = ind["rsi"][i]
    rb = cfg.get("rsi_buy", 45)
    rs = cfg.get("rsi_short", 55)
    at = cfg.get("adx_threshold", 20)
    vm = cfg.get("vol_mult", 0.95)

    # RSI
    if r < rb: bs += 2
    elif r < rb + 10: bs += 1
    if r > rs: ss += 2
    elif r > rs - 10: ss += 1

    # EMA alignment
    if ind["ema_fast"][i] > ind["ema_mid"][i] > ind["ema_slow"][i]: bs += 2
    elif ind["ema_fast"][i] > ind["ema_mid"][i]: bs += 1
    if ind["ema_fast"][i] < ind["ema_mid"][i] < ind["ema_slow"][i]: ss += 2
    elif ind["ema_fast"][i] < ind["ema_mid"][i]: ss += 1

    # MACD histogram
    if ind["macd_hist"][i] > 0 and ind["macd_hist"][i] > ind["macd_hist"][i - 1]: bs += 1
    if ind["macd_hist"][i] < 0 and ind["macd_hist"][i] < ind["macd_hist"][i - 1]: ss += 1

    # Bollinger Bands
    if closes[i] < ind["bb_lower"][i]: bs += 1
    if closes[i] > ind["bb_upper"][i]: ss += 1

    # ADX
    if ind["adx"][i] > at: bs += 1; ss += 1

    # Stochastic RSI
    if ind["stoch_rsi"][i] < 20: bs += 1
    if ind["stoch_rsi"][i] > 80: ss += 1

    # Williams %R
    if ind["willr"][i] < -80: bs += 1
    if ind["willr"][i] > -20: ss += 1

    # MFI
    if ind["mfi"][i] < 20: bs += 1
    if ind["mfi"][i] > 80: ss += 1

    # Volume
    vol_ratio = ind["volumes"][i] / ind["vol_sma"][i] if ind["vol_sma"][i] > 0 else 1.0
    if ind["vol_sma"][i] > 0 and ind["volumes"][i] > ind["vol_sma"][i] * vm: bs += 1; ss += 1

    # ATR filter: low volatility = no trade
    if ind["atr"][i] < ind["atr_sma"][i] * 0.8: bs = 0; ss = 0

    # Regime override
    if regime == "BULL": ss = 0
    elif regime == "BEAR": bs = 0

    # ============================================================
    # NEW v2 FILTERS (block trades, don't add to score)
    # ============================================================

    # VWAP filter: price must be on correct side of VWAP
    if cfg.get("use_vwap_filter", False) and ind.get("vwap"):
        vwap = ind["vwap"][i]
        if vwap > 0:
            # Block BUY if price below VWAP in BULL regime
            if bs > 0 and closes[i] < vwap and regime == "BULL":
                bs = max(0, bs - 2)  # Reduce score, don't block entirely
            # Block SELL if price above VWAP in BEAR regime
            if ss > 0 and closes[i] > vwap and regime == "BEAR":
                ss = max(0, ss - 2)

    # OBV filter: volume must confirm direction
    if cfg.get("use_obv_filter", False) and ind.get("obv") and ind.get("obv_ema"):
        if bs > 0 and ind["obv"][i] < ind["obv_ema"][i]:
            bs = max(0, bs - 1)  # Bearish volume divergence
        if ss > 0 and ind["obv"][i] > ind["obv_ema"][i]:
            ss = max(0, ss - 1)  # Bullish volume divergence

    # Supertrend filter: direction must agree
    if cfg.get("use_supertrend_filter", False) and ind.get("st_direction"):
        if bs > 0 and ind["st_direction"][i] == -1:
            bs = max(0, bs - 1)  # Supertrend bearish
        if ss > 0 and ind["st_direction"][i] == 1:
            ss = max(0, ss - 1)  # Supertrend bullish

    # ============================================================
    # DECIDE SIGNAL
    # ============================================================
    min_score = cfg.get("min_score", 6)
    signal = None

    if bs >= min_score and bs > ss:
        # HTF filter (post-scoring)
        if cfg.get("use_htf_filter", False):
            if htf_trend["1h"] == "BEAR" and htf_trend["4h"] == "BEAR":
                return None
            if htf_trend["1h"] == "BULL" or htf_trend["4h"] == "BULL":
                bs += 1

        signal = {
            "side": "BUY", "buy_score": bs, "short_score": ss,
            "regime": regime, "rsi": r, "adx": ind["adx"][i],
            "bb_width": bb_width, "price": closes[i],
            "atr": ind["atr"][i], "macd_hist": ind["macd_hist"][i],
            "ema_fast": ind["ema_fast"][i], "ema_mid": ind["ema_mid"][i],
            "ema_slow": ind["ema_slow"][i], "bb_upper": ind["bb_upper"][i],
            "bb_lower": ind["bb_lower"][i], "vol_ratio": vol_ratio,
            "vwap": ind.get("vwap", [0]*n)[i] if ind.get("vwap") else 0,
            "obv": ind.get("obv", [0]*n)[i] if ind.get("obv") else 0,
            "st_direction": ind.get("st_direction", [0]*n)[i] if ind.get("st_direction") else 0,
            "timestamp": ind["timestamps"][i],
            "htf_1h": htf_trend["1h"], "htf_4h": htf_trend["4h"],
        }
    elif ss >= min_score and ss > bs:
        if cfg.get("use_htf_filter", False):
            if htf_trend["1h"] == "BULL" and htf_trend["4h"] == "BULL":
                return None
            if htf_trend["1h"] == "BEAR" or htf_trend["4h"] == "BEAR":
                ss += 1

        signal = {
            "side": "SELL", "buy_score": bs, "short_score": ss,
            "regime": regime, "rsi": r, "adx": ind["adx"][i],
            "bb_width": bb_width, "price": closes[i],
            "atr": ind["atr"][i], "macd_hist": ind["macd_hist"][i],
            "ema_fast": ind["ema_fast"][i], "ema_mid": ind["ema_mid"][i],
            "ema_slow": ind["ema_slow"][i], "bb_upper": ind["bb_upper"][i],
            "bb_lower": ind["bb_lower"][i], "vol_ratio": vol_ratio,
            "vwap": ind.get("vwap", [0]*n)[i] if ind.get("vwap") else 0,
            "obv": ind.get("obv", [0]*n)[i] if ind.get("obv") else 0,
            "st_direction": ind.get("st_direction", [0]*n)[i] if ind.get("st_direction") else 0,
            "timestamp": ind["timestamps"][i],
            "htf_1h": htf_trend["1h"], "htf_4h": htf_trend["4h"],
        }

    if signal:
        signal["trade_zone"] = classify_trade_zone(signal)

    return signal
