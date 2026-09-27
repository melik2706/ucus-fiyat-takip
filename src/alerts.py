"""Fiyat karşılaştırma kuralları: yeni en düşük fiyat ve hedef fiyat uyarıları."""
from dataclasses import dataclass

from .models import Flight, fits_plan, is_pinned


@dataclass(frozen=True)
class Alert:
    flight: Flight
    reasons: tuple[str, ...]  # "new_low" | "target" | "new_flight"
    previous_min: int | None


def evaluate(flights: list[Flight], state: dict, cfg: dict, now_iso: str) -> tuple[dict, list[Alert]]:
    """Yeni state ve (sadece plana uyan uçuşlar için) uyarı listesini döndürür.

    Girdi state'i değiştirilmez; yeni bir kopya üretilir.
    """
    old = state.get("flights", {})
    is_first_run = not old
    target = cfg["target_price"]
    new_flights = dict(old)
    alerts: list[Alert] = []

    for f in flights:
        prev = old.get(f.key)
        prev_min = prev["min_price"] if prev else None
        prev_target_alert = prev.get("target_alerted_price") if prev else None

        reasons = []
        if prev is None and not is_first_run:
            reasons.append("new_flight")
        if prev_min is not None and f.price < prev_min:
            reasons.append("new_low")
        hits_target = f.price <= target and (prev_target_alert is None or f.price < prev_target_alert)
        if hits_target:
            reasons.append("target")

        plan_ok = fits_plan(f, cfg["plan"]) or is_pinned(f, cfg.get("pinned_flights", []))
        if reasons and plan_ok:
            alerts.append(Alert(flight=f, reasons=tuple(reasons), previous_min=prev_min))

        new_flights[f.key] = {
            "leg": f.leg,
            "price": f.price,
            "min_price": min(f.price, prev_min) if prev_min is not None else f.price,
            "first_seen": prev["first_seen"] if prev else now_iso,
            "last_seen": now_iso,
            "fits_plan": plan_ok,
            "target_alerted_price": f.price if (hits_target and plan_ok) else prev_target_alert,
        }

    return {**state, "flights": new_flights}, alerts


def best_combo(flights: list[Flight], plan: dict) -> tuple[Flight, Flight] | None:
    """Plana uyan en ucuz gidiş + en ucuz dönüş."""
    outs = [f for f in flights if f.leg == "outbound" and fits_plan(f, plan)]
    rets = [f for f in flights if f.leg == "return" and fits_plan(f, plan)]
    if not outs or not rets:
        return None
    return min(outs, key=lambda f: f.price), min(rets, key=lambda f: f.price)
