# Telegram Message Format Reference

## Overview
HTML-formatted message templates for Bitunix Futures trading bot Telegram notifications.

## Message Structure

```html
🤖 <b>Bitunix Futures Bot</b>
⏰ 2026-07-26 21:52:50
==============================

💰 <b>Account:</b>
  Available: $0.00
  Margin: $0.00
  PNL: $0.00

📊 <b>Open Positions:</b>
  BTCUSDT: LONG $100 PNL: $5.23

📈 <b>Market Analysis:</b>
  ⚪ BTCUSDT: $64,105.49 | RANGE | ADX:1 | RSI:29
  ⚪ ETHUSDT: $1,841.61 | RANGE | ADX:5 | RSI:30
  🟢 XRPUSDT: $1.09 | RANGE | ADX:17 | RSI:36
  ⚪ BNBUSDT: $569.44 | BULL | ADX:21 | RSI:46
  ⚪ DOGEUSDT: $0.07 | RANGE | ADX:2 | RSI:41
  
  ⚡ <b>BUY</b> @ $64,105.49
    TP: $65,200.00 | SL: $63,500.00

🎯 <b>1 Signal(s)!</b>
  BUY BTCUSDT @ $64,105.49
  TP: $65,200.00 | SL: $63,500.00
  📝 DRY RUN — No order placed

==============================
💰 Balance: $1,000.00
📊 Trades: 0
🔒 Mode: DRY RUN
```

## HTML Tags Used

| Tag | Purpose | Example |
|-----|---------|---------|
| `<b>` | Bold | `<b>Bitunix Futures Bot</b>` |
| `<i>` | Italic | `<i>Market Analysis</i>` |
| `<code>` | Monospace | `<code>BUY BTCUSDT</code>` |
| `<pre>` | Preformatted | `<pre>code block</pre>` |

## Emoji Legend

| Emoji | Meaning |
|-------|---------|
| 🤖 | Bot header |
| ⏰ | Timestamp |
| 💰 | Account/balance |
| 📊 | Positions |
| 📈 | Market analysis |
| 🟢 | BUY signal |
| 🔴 | SELL signal |
| ⚪ | Neutral/no signal |
| ⚡ | Active signal |
| 🎯 | Signals summary |
| 📝 | DRY RUN note |
| 📤 | Order placed |
| 📌 | TP/SL set |
| ❌ | Error |
| ✅ | Success |
| 🔒 | Mode indicator |

## Signal Line Format

```python
# Neutral
"  ⚪ {pair}: ${price:,.2f} | {regime} | ADX:{adx:.0f} | RSI:{rsi:.0f}"

# Buy signal
"  🟢 {pair}: ${price:,.2f} | {regime} | ADX:{adx:.0f} | RSI:{rsi:.0f}"
"  ⚡ <b>BUY</b> @ ${price:,.2f}"
"    TP: ${tp:,.2f} | SL: ${sl:,.2f}"

# Sell signal
"  🔴 {pair}: ${price:,.2f} | {regime} | ADX:{adx:.0f} | RSI:{rsi:.0f}"
"  ⚡ <b>SELL</b> @ ${price:,.2f}"
"    TP: ${tp:,.2f} | SL: ${sl:,.2f}"
```

## Send Function

```python
import requests

TG_TOKEN = "your_bot_token"
TG_CHAT = "your_chat_id"

def send_telegram(msg):
    """Send HTML-formatted message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT,
            "text": msg,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None
```

## Rate Limits

- **Max message length:** 4096 characters
- **Rate limit:** 30 messages/second (bot-wide)
- **Per chat:** 1 message/second recommended

## Error Handling

```python
def send_telegram_safe(msg):
    """Send with retry and truncation"""
    max_len = 4000  # Leave room for safety
    if len(msg) > max_len:
        msg = msg[:max_len] + "\n\n<i>[Truncated]</i>"
    
    for attempt in range(3):
        try:
            result = send_telegram(msg)
            if result and result.get('ok'):
                return True
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return False
```

## Complete Example

```python
def build_report(account, positions, signals, state):
    """Build complete Telegram report"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    msg = f"🤖 <b>Bitunix Futures Bot</b>\n"
    msg += f"⏰ {now}\n"
    msg += f"{'='*30}\n\n"
    
    # Account
    msg += f"💰 <b>Account:</b>\n"
    if account.get('code') == 0 and account.get('data'):
        d = account['data']
        msg += f"  Available: ${float(d.get('available', 0)):,.2f}\n"
        msg += f"  Margin: ${float(d.get('margin', 0)):,.2f}\n"
        msg += f"  PNL: ${float(d.get('crossUnrealizedPNL', 0)):,.2f}\n"
    
    # Positions
    msg += f"\n📊 <b>Open Positions:</b>\n"
    if positions.get('code') == 0 and positions.get('data'):
        for p in positions['data']:
            msg += f"  {p.get('symbol')}: {p.get('side')} ${p.get('available')} PNL: ${p.get('unrealizedPnl', 0)}\n"
    else:
        msg += "  None\n"
    
    # Analysis
    msg += f"\n📈 <b>Market Analysis:</b>\n"
    for s in signals:
        icon = "🟢" if s['signal'] == 'BUY' else "🔴" if s['signal'] == 'SELL' else "⚪"
        msg += f"  {icon} {s['symbol']}: ${s['price']:,.2f} | {s['regime']} | ADX:{s['adx']:.0f} | RSI:{s['rsi']:.0f}\n"
        if s['signal']:
            msg += f"  ⚡ <b>{s['signal']}</b> @ ${s['price']:,.2f}\n"
            msg += f"    TP: ${s['tp']:,.2f} | SL: ${s['sl']:,.2f}\n"
    
    # Summary
    active = [s for s in signals if s['signal']]
    if active:
        msg += f"\n🎯 <b>{len(active)} Signal(s)!</b>\n"
        for s in active:
            msg += f"  {s['signal']} {s['symbol']} @ ${s['price']:,.2f}\n"
            msg += f"  TP: ${s['tp']:,.2f} | SL: ${s['sl']:,.2f}\n"
            if not DRY_RUN:
                msg += f"  📤 Order placed\n"
                msg += f"  📌 TP/SL set\n"
            else:
                msg += f"  📝 DRY RUN — No order placed\n"
    else:
        msg += "\n⏸️ No signals — all pairs neutral\n"
    
    # Footer
    msg += f"\n{'='*30}"
    msg += f"\n💰 Balance: ${state['balance']:,.2f}"
    msg += f"\n📊 Trades: {len(state['trades'])}"
    msg += f"\n🔒 Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}"
    
    return msg
```

## Message Length Guidelines

- **Header:** ~50 chars
- **Account:** ~100 chars
- **Positions:** ~50 chars per position
- **Analysis:** ~80 chars per pair
- **Signals:** ~100 chars per signal
- **Footer:** ~80 chars
- **Total (5 pairs, 1 signal):** ~800 chars (well under 4096 limit)