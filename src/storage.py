"""State (JSON) ve fiyat geçmişi (CSV) dosyaları."""
import csv
import json
from pathlib import Path

from .models import Flight

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_FILE = DATA_DIR / "state.json"
HISTORY_FILE = DATA_DIR / "price_history.csv"
HISTORY_HEADER = ["checked_at", "leg", "origin", "dest", "departure", "arrival", "airline", "price", "google", "kiwi"]


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def append_history(flights: list[Flight], checked_at: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    is_new = not HISTORY_FILE.exists()
    with HISTORY_FILE.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if is_new:
            w.writerow(HISTORY_HEADER)
        for f in flights:
            w.writerow([
                checked_at, f.leg, f.origin, f.dest,
                f"{f.departure:%Y-%m-%d %H:%M}", f"{f.arrival:%Y-%m-%d %H:%M}", f.airline, f.price,
                dict(f.sources).get("Google", ""), dict(f.sources).get("Kiwi", ""),
            ])
