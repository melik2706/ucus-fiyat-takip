"""Telegram mesaj metinleri (HTML)."""
from html import escape

from .alerts import Alert, best_combo
from .models import Flight, fits_plan, is_pinned

AYLAR = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
KIWI_NOTE = "Not: Kiwi fiyatına Kiwi'nin hizmet bedeli dahildir; Google fiyatı genelde havayolunun kendi fiyatıdır."
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
        + _sources_text(f)
    )


def _sources_text(f: Flight) -> str:
    if len(f.sources) < 2:
        return ""
    return " (" + " · ".join(f"{name} {tl(price)}" for name, price in f.sources) + ")"


def cross_check(f: Flight, previous: tuple[tuple[str, int], ...]) -> str:
    """İki kaynağı karşılaştırıp düşüşün gerçek olup olmadığına karar verir."""
    now = dict(f.sources)
    before = dict(previous)
    if len(now) < 2:
        only = next(iter(now), "tek kaynak")
        return f"ℹ️ Bu kontrolde sadece {only} verisi alındı, çapraz kontrol yapılamadı."
    compared = [n for n in now if n in before]
    dropped = [n for n in compared if now[n] < before[n]]
    parts = [
        f"{n} {tl(now[n])}" + (f" (önce {tl(before[n])})" if n in before and before[n] != now[n] else "")
        for n in sorted(now)
    ]
    detail = "Kaynaklar: " + " · ".join(parts)
    if compared and len(dropped) == len(compared):
        verdict = "✅ Çapraz kontrol: iki kaynakta da düştü, gerçek bir indirim."
    elif dropped:
        verdict = f"⚠️ Sadece {', '.join(dropped)} tarafında düştü; o siteden kontrol ederek al."
    else:
        verdict = "Çapraz kontrol: kaynaklarda düşüş yok (hedef fiyat uyarısı)."
    return f"{detail}\n{verdict}"


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
        line += "\n" + cross_check(a.flight, a.previous_sources)
        parts.append(line + "\n")
    parts.append(_combo_block(flights, cfg["plan"]))
    parts.append(f"\nHedef fiyat: {tl(cfg['target_price'])}")
    parts.append(KIWI_NOTE)
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
    lines += ["", _combo_block(flights, plan), f"\nHedef fiyat: {tl(cfg['target_price'])}", KIWI_NOTE]
    return "\n".join(lines)
