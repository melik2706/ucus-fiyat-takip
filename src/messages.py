"""Telegram mesaj metinleri (HTML)."""
from html import escape

from .alerts import Alert, best_combo
from .models import Flight, fits_plan, is_pinned

AYLAR = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
REASON_TEXT = {
    "new_low": "📉 Yeni en düşük fiyat",
    "target": "🎯 Hedef fiyatın altında",
    "new_flight": "🆕 Yeni uçuş eklendi",
}


def tl(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + " TL"


def flight_line(f: Flight, pinned: list[dict] | None = None) -> str:
    d = f.departure
    star = "⭐ " if pinned and is_pinned(f, pinned) else ""
    return (
        f"{star}{d.day} {AYLAR[d.month]} {d:%H:%M}→{f.arrival:%H:%M} "
        f"{f.origin}→{f.dest} {escape(f.airline)} — <b>{tl(f.price)}</b>"
    )


def _combo_block(flights: list[Flight], plan: dict) -> str:
    combo = best_combo(flights, plan)
    if not combo:
        return "Plana uyan gidiş+dönüş kombinasyonu şu an yok."
    out, ret = combo
    return (
        "<b>En ucuz plan (gidiş+dönüş):</b>\n"
        f"🛫 {flight_line(out)}\n🛬 {flight_line(ret)}\n"
        f"Toplam: <b>{tl(out.price + ret.price)}</b>"
    )


def alert_message(alerts: list[Alert], flights: list[Flight], cfg: dict) -> str:
    parts = ["✈️ <b>Uçuş fiyat uyarısı</b>\n"]
    for a in alerts:
        reasons = " · ".join(REASON_TEXT[r] for r in a.reasons)
        line = f"{reasons}\n{flight_line(a.flight)}"
        if a.previous_min is not None and a.flight.price < a.previous_min:
            diff = a.previous_min - a.flight.price
            line += f"\n(önceki en düşük {tl(a.previous_min)}, −{tl(diff)})"
        parts.append(line + "\n")
    parts.append(_combo_block(flights, cfg["plan"]))
    parts.append(f"\nHedef fiyat: {tl(cfg['target_price'])}")
    link = alerts[0].flight.search_url if alerts else ""
    if link:
        parts.append(f'<a href="{escape(link)}">Google Flights\'ta aç</a>')
    return "\n".join(parts)


def summary_message(flights: list[Flight], cfg: dict, title: str) -> str:
    plan = cfg["plan"]
    pinned = cfg.get("pinned_flights", [])
    fitting = sorted(
        (f for f in flights if fits_plan(f, plan) or is_pinned(f, pinned)), key=lambda f: f.departure
    )
    lines = [f"📋 <b>{escape(title)}</b>\n", "<b>Plana uyan uçuşlar:</b>"]
    lines += [("🛫 " if f.leg == "outbound" else "🛬 ") + flight_line(f, pinned) for f in fitting] or ["(yok)"]
    lines += ["", _combo_block(flights, plan), f"\nHedef fiyat: {tl(cfg['target_price'])}"]
    return "\n".join(lines)
