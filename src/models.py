"""Uçuş veri modeli ve plan uygunluk kontrolü."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

TR_TZ = timezone(timedelta(hours=3))  # Türkiye kalıcı olarak UTC+3


@dataclass(frozen=True)
class Flight:
    leg: str  # "outbound" | "return"
    origin: str
    dest: str
    departure: datetime  # yerel saat (naive)
    arrival: datetime
    airline: str
    price: int  # kaynaklar arasındaki en düşük fiyat
    search_url: str = ""
    sources: tuple[tuple[str, int], ...] = ()  # (("Google", 2200), ("Kiwi", 2701))

    @property
    def key(self) -> str:
        # Aynı rota + aynı kalkış dakikası tek bir direkt uçuştur; havayolu adı kaynağa göre değişebilir
        return f"{self.origin}-{self.dest}_{self.departure:%Y-%m-%dT%H:%M}"


def merge_sources(flights: list[Flight]) -> list[Flight]:
    """Farklı kaynaklardan gelen aynı uçuşları tek kayıtta birleştirir (fiyat = en düşük)."""
    grouped: dict[str, list[Flight]] = {}
    for f in flights:
        grouped.setdefault(f.key, []).append(f)
    merged = []
    for group in grouped.values():
        prices: dict[str, int] = {}
        for f in group:
            for name, price in f.sources:
                prices[name] = min(price, prices.get(name, price))
        base = next((f for f in group if f.search_url), group[0])
        if not prices:
            merged.append(min(group, key=lambda f: f.price))
            continue
        merged.append(
            replace(base, price=min(prices.values()), sources=tuple(sorted(prices.items())))
        )
    return merged


def is_pinned(flight: Flight, pinned: list[dict]) -> bool:
    """Kullanıcının 'mutlaka takip et' dediği uçuşlardan biri mi?"""
    return any(
        p["origin"] == flight.origin
        and p["dest"] == flight.dest
        and datetime.fromisoformat(p["departure"]) == flight.departure
        for p in pinned
    )


def missing_pinned(flights: list[Flight], pinned: list[dict]) -> list[dict]:
    """Bu kontrolde sonuçlarda bulunamayan sabitlenmiş uçuşlar."""
    return [p for p in pinned if not any(is_pinned(f, [p]) for f in flights)]


def fits_plan(flight: Flight, plan: dict) -> bool:
    """Uçuş kullanıcının planına (08:30 toplantı, 14:00 sonrası dönüş) uyuyor mu?"""
    if flight.leg == "outbound":
        return (
            flight.departure >= datetime.fromisoformat(plan["outbound_depart_after"])
            and flight.arrival <= datetime.fromisoformat(plan["outbound_arrive_by"])
        )
    return (
        datetime.fromisoformat(plan["return_depart_after"])
        <= flight.departure
        <= datetime.fromisoformat(plan["return_depart_before"])
    )
