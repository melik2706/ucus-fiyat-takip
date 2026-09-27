"""Telegram chat ID'sini bulur ve test mesajı yollar.

1. Telegram'da @BotFather'a /newbot yaz, token'ı al.
2. Oluşan bota Telegram'dan herhangi bir mesaj at (örn. "merhaba").
3. python telegram_setup.py <BOT_TOKEN>
"""
import json
import sys
import urllib.request


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    token = sys.argv[1]
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20) as r:
        updates = json.loads(r.read()).get("result", [])
    chats = {u["message"]["chat"]["id"] for u in updates if "message" in u}
    if not chats:
        print("Mesaj bulunamadı. Önce bota Telegram'dan bir mesaj gönder, sonra tekrar çalıştır.")
        return 1
    chat_id = chats.pop()
    payload = json.dumps({"chat_id": chat_id, "text": "✅ Uçuş fiyat takibi bağlantısı çalışıyor."}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=20).read()
    print(f"TELEGRAM_CHAT_ID = {chat_id}  (Telegram'a test mesajı gönderildi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
