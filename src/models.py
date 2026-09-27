"""Uçuş veri modeli ve plan uygunluk kontrolü."""
from dataclasses import dataclass
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
    price: int
    search_url: str = ""

    @property
    def key(self) -> str:
        return f"{self.origin}-{self.dest}_{self.departure:%Y-%m-%dT%H:%M}_{self.airline}"


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
