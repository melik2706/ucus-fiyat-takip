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
from src.fetch import fetch_search as google_fetch
from src.kiwi import fetch_search as kiwi_fetch
from src.messages import alert_message, summary_message
from src.models import TR_TZ, Flight, merge_sources, missing_pinned

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
FETCH_RETRIES = 3
RETRY_DELAY_SEC = (15, 40)
# Düzenli bir robot izi bırakmamak için: başlangıç saati ve sorgular arası bekleme rastgele
START_JITTER_SEC = (0, 180)
BETWEEN_QUERIES_SEC = (3, 12)


SOURCES = {"Google": google_fetch, "Kiwi": kiwi_fetch}


def _fetch_with_retry(fetch, search: dict, currency: str, label: str, jitter: bool) -> list[Flight]:
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            return fetch(search, currency)
        except Exception as exc:  # ağ/parsing hataları: tekrar dene, sonra üst katmana bildir
            print(f"{label}: hata (deneme {attempt}): {exc}")
            if attempt == FETCH_RETRIES:
                raise
            time.sleep(random.uniform(*RETRY_DELAY_SEC) if jitter else 2)
    return []


def fetch_all(cfg: dict, jitter: bool) -> tuple[list[Flight], list[str], set[tuple[str, str, str]]]:
    """Tüm aramaları tüm kaynaklardan çeker ve aynı uçuşları birleştirir."""
    raw: list[Flight] = []
    errors: list[str] = []
    succeeded: set[tuple[str, str, str]] = set()
    jobs = [(name, s) for s in cfg["searches"] for name in SOURCES]
    for i, (name, search) in enumerate(random.sample(jobs, k=len(jobs))):  # sıra her seferinde farklı
        if jitter and i > 0:
            time.sleep(random.uniform(*BETWEEN_QUERIES_SEC))
        label = f"[{name}] {search['date']} {search['from']}→{search['to']}"
        try:
            found = _fetch_with_retry(SOURCES[name], search, cfg["currency"], label, jitter)
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            continue
        print(f"{label}: {len(found)} direkt uçuş")
        raw.extend(found)
        succeeded.add((search["date"], search["from"], search["to"]))
    return merge_sources(raw), errors, succeeded


def run(dry_run: bool) -> int:
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    now = datetime.now(TR_TZ)
    today = now.date().isoformat()
    if now.date() > date.fromisoformat(cfg["track_until"]):
        print("Takip tarihi geçti, çıkılıyor.")
        return 0

    quiet_start, quiet_end = cfg["quiet_hours_tr"]
    is_quiet = quiet_start <= now.hour < quiet_end  # gece: bildirimler sessiz gider

    def notify(text: str) -> None:
        print("\n----- MESAJ -----\n" + text + "\n-----------------")
        if not dry_run:
            telegram.send(text, silent=is_quiet)

    jitter = bool(os.environ.get("CI") or os.environ.get("TRACKER_JITTER"))  # sadece sunucuda rastgele bekle
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

    # Özet saatleri (örn. 09:00 ve 21:00): o saatten sonraki ilk kontrolde bir kez gönderilir
    passed = [h for h in cfg["summary_hours_tr"] if now.hour >= h]
    slot = f"{today}-{max(passed)}" if passed else None

    if is_first_run:
        notify(summary_message(flights, cfg, "Uçuş fiyat takibi başladı"))
        new_state = {**new_state, "last_summary_slot": slot}
    elif alerts:
        notify(alert_message(alerts, flights, cfg))

    if slot and new_state.get("last_summary_slot") != slot:
        checks = new_state.get("checks_since_summary", 0) + 1
        title = f"Özet — {now:%d.%m.%Y %H:%M} (son özetten beri {checks} kontrol)"
        notify(summary_message(flights, cfg, title))
        new_state = {**new_state, "last_summary_slot": slot, "checks_since_summary": 0}
    else:
        new_state = {**new_state, "checks_since_summary": new_state.get("checks_since_summary", 0) + 1}

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
