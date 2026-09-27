from datetime import datetime

from src.alerts import best_combo, evaluate
from src.messages import alert_message, summary_message
from src.models import Flight, fits_plan, is_pinned, missing_pinned

CFG = {
    "target_price": 2000,
    "pinned_flights": [{"origin": "GZT", "dest": "ESB", "departure": "2026-11-02T21:20"}],
    "plan": {
        "outbound_depart_after": "2026-11-02T17:00",
        "outbound_arrive_by": "2026-11-03T07:45",
        "return_depart_after": "2026-11-03T15:30",
        "return_depart_before": "2026-11-04T03:00",
    },
}


def fl(leg, dep, arr, price, origin="GZT", dest="ESB"):
    if leg == "return":
        origin, dest = "ESB", "GZT"
    return Flight(leg, origin, dest, datetime.fromisoformat(dep), datetime.fromisoformat(arr), "AJet", price)


EARLY = fl("outbound", "2026-11-03T04:50", "2026-11-03T06:05", 2200)
LATE_MORNING = fl("outbound", "2026-11-03T09:45", "2026-11-03T11:00", 1500)
PINNED = fl("outbound", "2026-11-02T21:20", "2026-11-02T22:35", 2189)
EVENING_RET = fl("return", "2026-11-03T19:25", "2026-11-03T20:40", 2214)
MORNING_RET = fl("return", "2026-11-03T07:50", "2026-11-03T09:05", 1200)


def test_plan_fit_rules():
    assert fits_plan(EARLY, CFG["plan"])
    assert fits_plan(PINNED, CFG["plan"])
    assert not fits_plan(LATE_MORNING, CFG["plan"])  # 08:30 toplantıya yetişmez
    assert fits_plan(EVENING_RET, CFG["plan"])
    assert not fits_plan(MORNING_RET, CFG["plan"])  # iş bitmeden kalkıyor


def test_first_run_records_state_without_drop_alerts():
    state, alerts = evaluate([EARLY, EVENING_RET], {}, CFG, "t0")
    assert alerts == []
    assert state["flights"][EARLY.key]["min_price"] == 2200


def test_price_drop_triggers_new_low_alert():
    state, _ = evaluate([EARLY], {}, CFG, "t0")
    cheaper = fl("outbound", "2026-11-03T04:50", "2026-11-03T06:05", 2100)
    new_state, alerts = evaluate([cheaper], state, CFG, "t1")
    assert [a.reasons for a in alerts] == [("new_low",)]
    assert alerts[0].previous_min == 2200
    assert new_state["flights"][EARLY.key]["min_price"] == 2100
    assert state["flights"][EARLY.key]["min_price"] == 2200  # girdi değişmedi


def test_price_rise_does_not_alert():
    state, _ = evaluate([EARLY], {}, CFG, "t0")
    pricier = fl("outbound", "2026-11-03T04:50", "2026-11-03T06:05", 2500)
    _, alerts = evaluate([pricier], state, CFG, "t1")
    assert alerts == []


def test_target_alert_fires_once_per_price_level():
    cheap = fl("outbound", "2026-11-03T04:50", "2026-11-03T06:05", 1900)
    state, alerts = evaluate([cheap], {}, CFG, "t0")
    assert alerts[0].reasons == ("target",)
    state, alerts = evaluate([cheap], state, CFG, "t1")
    assert alerts == []  # aynı fiyat için tekrar uyarma
    cheaper = fl("outbound", "2026-11-03T04:50", "2026-11-03T06:05", 1800)
    _, alerts = evaluate([cheaper], state, CFG, "t2")
    assert set(alerts[0].reasons) == {"new_low", "target"}


def test_non_plan_flights_are_tracked_but_not_alerted():
    state, _ = evaluate([LATE_MORNING, MORNING_RET], {}, CFG, "t0")
    assert LATE_MORNING.key in state["flights"]
    cheaper = fl("outbound", "2026-11-03T09:45", "2026-11-03T11:00", 900)
    _, alerts = evaluate([cheaper], state, CFG, "t1")
    assert alerts == []


def test_pinned_flight_helpers():
    assert is_pinned(PINNED, CFG["pinned_flights"])
    assert not is_pinned(EARLY, CFG["pinned_flights"])
    assert missing_pinned([EARLY], CFG["pinned_flights"]) == CFG["pinned_flights"]
    assert missing_pinned([PINNED], CFG["pinned_flights"]) == []


def test_best_combo_picks_cheapest_fitting_pair():
    out, ret = best_combo([EARLY, PINNED, LATE_MORNING, EVENING_RET, MORNING_RET], CFG["plan"])
    assert out == PINNED and ret == EVENING_RET


def test_messages_render():
    flights = [EARLY, PINNED, EVENING_RET]
    s = summary_message(flights, CFG, "Test")
    assert "⭐ 2 Kas 21:20→22:35" in s and "4.403 TL" in s
    state, _ = evaluate(flights, {}, CFG, "t0")
    cheaper = fl("outbound", "2026-11-02T21:20", "2026-11-02T22:35", 1950)
    _, alerts = evaluate([cheaper], state, CFG, "t1")
    msg = alert_message(alerts, [cheaper, EVENING_RET], CFG)
    assert "−239 TL" in msg and "Hedef fiyatın altında" in msg


def src(flight, *pairs):
    from dataclasses import replace
    return replace(flight, price=min(p for _, p in pairs), sources=tuple(pairs))


def test_merge_combines_same_flight_from_two_sources():
    from src.models import merge_sources
    g = src(EARLY, ("Google", 2200))
    k = src(EARLY, ("Kiwi", 2701))
    merged = merge_sources([g, k, src(EVENING_RET, ("Kiwi", 2300))])
    by_key = {f.key: f for f in merged}
    assert len(merged) == 2
    assert by_key[EARLY.key].price == 2200
    assert by_key[EARLY.key].sources == (("Google", 2200), ("Kiwi", 2701))


def test_cross_check_verdicts():
    from src.messages import cross_check
    both = src(EARLY, ("Google", 2100), ("Kiwi", 2600))
    assert "iki kaynakta da düştü" in cross_check(both, (("Google", 2200), ("Kiwi", 2701)))
    one = src(EARLY, ("Google", 2100), ("Kiwi", 2701))
    assert "Sadece Google" in cross_check(one, (("Google", 2200), ("Kiwi", 2701)))
    single = src(EARLY, ("Kiwi", 2600))
    assert "sadece Kiwi" in cross_check(single, (("Google", 2200),))


def test_alert_carries_previous_source_prices():
    state, _ = evaluate([src(EARLY, ("Google", 2200), ("Kiwi", 2701))], {}, CFG, "t0")
    _, alerts = evaluate([src(EARLY, ("Google", 2100), ("Kiwi", 2650))], state, CFG, "t1")
    assert alerts[0].previous_sources == (("Google", 2200), ("Kiwi", 2701))
    msg = alert_message(alerts, [alerts[0].flight], CFG)
    assert "iki kaynakta da düştü" in msg and "Kiwi 2.650 TL (önce 2.701 TL)" in msg
