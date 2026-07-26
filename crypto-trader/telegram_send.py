#!/usr/bin/env python3
"""Send message to Telegram via IP (bypasses DNS issue)."""
import requests, sys, warnings
warnings.filterwarnings('ignore')

BOT_TOKEN = "8658665295:AAE42kkzSFMfuskGfaJ-Qshc1jsZ_ekFvFs"
CHAT_ID = "8048000483"
API_IP = "149.154.167.220"

def send(text):
    r = requests.post(
        f"https://{API_IP}/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        headers={"Host": "api.telegram.org"},
        timeout=10, verify=False
    )
    return r.json()

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Test"
    result = send(msg)
    print("OK" if result.get("ok") else f"FAIL: {result}")
