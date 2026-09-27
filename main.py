"""Gaziantep ⇄ Ankara uçuş fiyat takibi.

Kullanım:
    python main.py            # kontrol et, gerekirse Telegram'a bildir
    python main.py --dry-run  # mesajları göndermeden ekrana yaz
"""
import json
import os
import random
import sys
import time
from datetime import date, datetime
from pathlib import Path

from src import storage, telegram
from src.alerts import evaluate
from src.fetch import fetch_search
from src.messages import alert_message, summary_message
from src.models import TR_TZ, Flight, missing_pinned

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
FETCH_RETRIES = 4
RETRY_DELAY_SEC = (20, 60)
# Düzenli bir robot izi bırakmamak için: başlangıç saati ve sorgular arası bekleme rastgele
START_JITTER_SEC = (0, 900)
BETWEEN_QUERIES_SEC = (6, 25)


def fetch_all(cfg: dict, jitter: bool) -> tuple[list[Flight], list[str], set[tuple[str, str, str]]]:
    flights: list[Flight] = []
    errors: list[str] = []
    succeeded: set[tuple[str, str, str]] = set()
    searches = random.sample(cfg["searches"], k=len(cfg["searches"]))  # sıra her seferinde farklı
    for i, search in enumerate(searches):
        if jitter and i > 0:
            time.sleep(random.uniform(*BETWEEN_QUERIES_SEC))
        label = f"{search['date']} {search['from']}→{search['to']}"
        for attempt in range(1, FETCH_RETRIES + 1):
            try:
                found = fetch_search(search, cfg["currency"])
                print(f"{label}: {len(found)} direkt uçuş")
                flights.extend(found)
                succeeded.add((search["date"], search["from"], search["to"]))
                break
            except Exception as exc:  # ağ/parsing hataları: tekrar dene, sonra raporla
                print(f"{label}: hata (deneme {attempt}): {exc}")
                if attempt == FETCH_RETRIES:
                    errors.append(f"{label}: {exc}")
                else:
                    time.sleep(random.uniform(*RETRY_DELAY_SEC))
    return flights, errors, succeeded


def run(dry_run: bool) -> int:
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    now = datetime.now(TR_TZ)
    today = now.date().isoformat()
    if now.date() > date.fromisoformat(cfg["track_until"]):
        print("Takip tarihi geçti, çıkılıyor.")
        return 0

    def notify(text: str) -> None:
        print("\n----- MESAJ -----\n" + text + "\n-----------------")
        if not dry_run:
            telegram.send(text)

    jitter = bool(os.environ.get("CI"))  # sadece bulutta (GitHub Actions) rastgele bekle
    if jitter:
        time.sleep(random.uniform(*START_JITTER_SEC))

    state = storage.load_state()
    flights, errors, succeeded = fetch_all(cfg, jitter)

    if not flights:
        failures = state.get("consecutive_failures", 0) + 1
        state = {**state, "consecutive_failures": failures}
        if failures == cfg["failure_alert_after"]:
            notify(f"⚠️ Uçuş takibi {failures} kez üst üste fiyat alamadı.\n" + "\n".join(errors))
        storage.save_state(state)
        return 1

    is_first_run = not state.get("flights")
    new_state, alerts = evaluate(flights, state, cfg, now.isoformat(timespec="minutes"))
    new_state = {**new_state, "consecutive_failures": 0, "last_check": now.isoformat(timespec="minutes")}

    if is_first_run:
        notify(summary_message(flights, cfg, "Uçuş fiyat takibi başladı"))
        new_state = {**new_state, "last_summary_date": today}
    elif alerts:
        notify(alert_message(alerts, flights, cfg))

    if now.hour >= cfg["daily_summary_hour_tr"] and new_state.get("last_summary_date") != today:
        notify(summary_message(flights, cfg, f"Günlük özet — {now:%d.%m.%Y}"))
        new_state = {**new_state, "last_summary_date": today}

    # Sadece araması başarılı olan rotalar için "kayboldu" uyarısı ver
    checkable = [
        p for p in cfg.get("pinned_flights", [])
        if (p["departure"][:10], p["origin"], p["dest"]) in succeeded
    ]
    missing = missing_pinned(flights, checkable)
    if missing and new_state.get("pinned_missing_warned") != today:
        notes = "\n".join(f"• {p.get('note', p['departure'])}" for p in missing)
        notify(f"⚠️ Sabitlenmiş uçuş bu kontrolde bulunamadı (dolmuş/iptal olabilir):\n{notes}")
        new_state = {**new_state, "pinned_missing_warned": today}

    storage.append_history(flights, now.isoformat(timespec="minutes"))
    storage.save_state(new_state)
    return 0


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
