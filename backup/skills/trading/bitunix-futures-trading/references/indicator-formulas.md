# Technical Indicator Formulas Reference

## Overview
Pure Python implementations of technical indicators used in Bitunix Futures trading bot. No external dependencies (numpy, pandas, ta-lib).

## EMA (Exponential Moving Average)

```python
def calc_ema(data, period):
    """Exponential Moving Average"""
    n = len(data)
    ema = [0.0] * n
    if n < 2:
        return ema
    ema[0] = data[0]
    multiplier = 2.0 / (period + 1)
    for i in range(1, n):
        ema[i] = data[i] * multiplier + ema[i-1] * (1 - multiplier)
    return ema
```

**Usage:** EMA 8, 25, 100 on 4H closes for regime detection.

---

## RSI (Relative Strength Index)

```python
def calc_rsi(closes, period=14):
    """RSI using Wilder's smoothing"""
    n = len(closes)
    rsi = [50.0] * n
    if n < period + 2:
        return rsi
    
    gains, losses = [], []
    for i in range(1, n):
        diff = closes[i] - closes[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    
    # Initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss > 0:
        rsi[period] = 100 - 100 / (1 + avg_gain / avg_loss)
    
    # Wilder's smoothing
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss > 0:
            rsi[i + 1] = 100 - 100 / (1 + avg_gain / avg_loss)
    
    return rsi
```

**Usage:** RSI 14 on 1H closes for entry timing.

---

## ADX (Average Directional Index)

```python
def calc_adx(highs, lows, closes, period=14):
    """ADX for trend strength"""
    n = len(closes)
    adx = [25.0] * n
    if n < period * 2 + 2:
        return adx
    
    plus_dm, minus_dm, tr = [], [], []
    for i in range(1, n):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
        
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        ))
    
    if len(tr) < period:
        return adx
    
    atr_sum = sum(tr[:period])
    pdm_sum = sum(plus_dm[:period])
    ndm_sum = sum(minus_dm[:period])
    
    for i in range(period, len(tr)):
        atr_sum = atr_sum - atr_sum/period + tr[i]
        pdm_sum = pdm_sum - pdm_sum/period + plus_dm[i]
        ndm_sum = ndm_sum - ndm_sum/period + minus_dm[i]
        
        pdi = 100 * pdm_sum / atr_sum if atr_sum > 0 else 0
        ndi = 100 * ndm_sum / atr_sum if atr_sum > 0 else 0
        dx = 100 * abs(pdi - ndi) / (pdi + ndi) if (pdi + ndi) > 0 else 0
        adx[i + 1] = dx
    
    return adx
```

**Usage:** ADX 14 on 4H for regime filter (ADX >= 20 = trending).

---

## MACD (Moving Average Convergence Divergence)

```python
def calc_macd(closes):
    """MACD with signal line and histogram"""
    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    
    macd = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal = calc_ema(macd, 9)
    histogram = [macd[i] - signal[i] for i in range(len(closes))]
    
    return macd, signal, histogram
```

**Usage:** MACD histogram on 1H for momentum confirmation.

---

## ATR (Average True Range)

```python
def calc_atr(highs, lows, closes, period=14):
    """ATR for volatility-based TP/SL"""
    n = len(closes)
    atr = [0.0] * n
    if n < 2:
        return atr
    
    tr = [max(
        highs[i] - lows[i],
        abs(highs[i] - closes[i-1]),
        abs(lows[i] - closes[i-1])
    ) for i in range(1, n)]
    
    if len(tr) < period:
        return atr
    
    atr[period] = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period
    
    return atr
```

**Usage:** ATR 14 on 1H for TP/SL calculation:
- TP = entry ± 2.5 × ATR
- SL = entry ∓ 1.5 × ATR

---

## Regime Detection Logic

```python
def detect_regime(ema8, ema25, ema100, adx, index):
    """Determine market regime from 4H indicators"""
    e8, e25, e100 = ema8[index], ema25[index], ema100[index]
    adx_val = adx[index]
    
    if e8 > e25 > e100 and adx_val > 20:
        return "BULL"
    elif e8 < e25 < e100 and adx_val > 20:
        return "BEAR"
    else:
        return "RANGE"
```

---

## Signal Generation

```python
def generate_signal(regime, e8, e25, rsi, macd_hist, index):
    """Generate BUY/SELL signal based on regime and 1H indicators"""
    if regime == "BULL":
        # Long only in bull trend
        if e8 > e25 and rsi[index] > 45 and macd_hist[index] > macd_hist[index-1]:
            return "BUY"
    elif regime == "BEAR":
        # Short only in bear trend
        if e8 < e25 and rsi[index] < 55 and macd_hist[index] < macd_hist[index-1]:
            return "SELL"
    elif regime == "RANGE":
        # Mean reversion in range
        if rsi[index] < 30 and macd_hist[index] > macd_hist[index-1]:
            return "BUY"
        elif rsi[index] > 70 and macd_hist[index] < macd_hist[index-1]:
            return "SELL"
    return None
---

## Complete Analysis Function (Implemented in paper_trading_bot.py)

```python
def analyze_pair(api, symbol):
    # Fetch data
    klines_1h = api.get_klines(symbol, "60")    # 60 = 1H
    klines_4h = api.get_klines(symbol, "240")   # 240 = 4H
    
    if not klines_1h.get('data') or len(klines_1h['data']) < 100: return None
    if not klines_4h.get('data') or len(klines_4h['data']) < 50: return None
    
    # Parse OHLC
    c1h = [float(k['close']) for k in klines_1h['data']]
    h1h = [float(k['high']) for k in klines_1h['data']]
    l1h = [float(k['low']) for k in klines_1h['data']]
    c4h = [float(k['close']) for k in klines_4h['data']]
    h4h = [float(k['high']) for k in klines_4h['data']]
    l4h = [float(k['low']) for k in klines_4h['data']]
    
    # Indicators
    e8 = calc_ema(c4h, 8)
    e25 = calc_ema(c4h, 25)
    e100 = calc_ema(c4h, 100)
    adx = calc_adx(h4h, l4h, c4h)
    rsi = calc_rsi(c1h)
    macd, sig, hist = calc_macd(c1h)
    atr = calc_atr(h1h, l1h, c1h)
    
    # Current indices (LAST CLOSED candles)
    i4h = len(c4h) - 1
    i1h = len(c1h) - 1
    price = c1h[i1h]
    
    # Regime
    if e8[i4h] > e25[i4h] > e100[i4h] and adx[i4h] >= 20: regime = "BULL"
    elif e8[i4h] < e25[i4h] < e100[i4h] and adx[i4h] >= 20: regime = "BEAR"
    else: regime = "RANGE"
    
    # Signals
    signal = None
    if regime == "BULL" and adx[i4h] >= 20:
        if e8[i4h] > e25[i4h] and rsi[i1h] > 45 and hist[i1h] > hist[i1h-1]:
            signal = "BUY"
    elif regime == "BEAR" and adx[i4h] >= 20:
        if e8[i4h] < e25[i4h] and rsi[i1h] < 55 and hist[i1h] < hist[i1h-1]:
            signal = "SELL"
    elif regime == "RANGE":
        if rsi[i1h] < 30 and hist[i1h] > hist[i1h-1]:
            signal = "BUY"
        elif rsi[i1h] > 70 and hist[i1h] < hist[i1h-1]:
            signal = "SELL"
    
    # TP/SL
    tp = sl = None
    atr_val = atr[i1h] if atr[i1h] > 0 else price * 0.01
    atr_pct = atr_val / price
    if signal == "BUY":
        tp = price * (1 + atr_pct * 2.5)
        sl = price * (1 - atr_pct * 1.5)
    elif signal == "SELL":
        tp = price * (1 - atr_pct * 2.5)
        sl = price * (1 + atr_pct * 1.5)
    
    return {
        'symbol': symbol, 'price': price, 'regime': regime,
        'signal': signal, 'adx': adx[i4h], 'rsi': rsi[i1h],
        'tp': tp, 'sl': sl, 'atr_pct': atr_pct
    }
```

---

## Look-Ahead Bias Fix (Critical - 2026-07-27 Session)

When using 4H indicators for 1H decisions:

```python
# WRONG - uses current (possibly unclosed) 4H candle
j4 = min(len(c4)-1, max(0, int((ts - four_h_times[0]) / 14400000)))

# WRONG - finds last 4H candle with OPEN time < current time (still open!)
j4 = 0
for jj in range(len(four_h_times)-1, -1, -1):
    if four_h_times[jj] < ts:
        j4 = jj
        break

# CORRECT - verifies candle is FULLY CLOSED
j4 = 0
for jj in range(len(four_h_times)-1, -1, -1):
    if four_h_times[jj] + 14400000 <= ts:  # 4h = 14400000 ms
        j4 = jj
        break

# A 4H candle at time T closes at T+14400000
# At 09:00, the 08:00 candle is still open (closes at 12:00)
# Last CLOSED candle is 04:00
```

The `paper_trading_bot.py` and `trading_bot.py` use `i4h = len(c4h) - 1` which correctly uses the LAST CLOSED 4H candle from the fetched data.

---

## TP/SL Calculation

```python
def calc_tp_sl(entry_price, atr_pct, signal):
    """ATR-based TP/SL"""
    if signal == "BUY":
        tp = entry_price * (1 + atr_pct * 2.5)
        sl = entry_price * (1 - atr_pct * 1.5)
    elif signal == "SELL":
        tp = entry_price * (1 - atr_pct * 2.5)
        sl = entry_price * (1 + atr_pct * 1.5)
    else:
        tp = sl = None
    return tp, sl

# Where atr_pct = atr_value / current_price
```

---

## Data Requirements

| Indicator | Min Bars | Timeframe |
|-----------|----------|-----------|
| EMA 100 | 100+ | 4H |
| ADX 14 | 30+ | 4H |
| RSI 14 | 16+ | 1H |
| MACD | 26+ | 1H |
| ATR 14 | 16+ | 1H |

**Recommended:** 200+ bars 1H, 100+ bars 4H