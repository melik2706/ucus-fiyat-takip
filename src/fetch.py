"""Google Flights'tan (fast-flights) direkt uçuş fiyatlarını çeker."""
from datetime import datetime

from fast_flights import FlightQuery, create_query, get_flights

from .models import Flight


def _to_dt(simple) -> datetime:
    y, m, d = simple.date
    hh, mm = (list(simple.time) + [0, 0])[:2]
    return datetime(y, m, d, hh or 0, mm or 0)


def fetch_search(search: dict, currency: str) -> list[Flight]:
    """Tek bir tarih/yön araması için direkt uçuşları döndürür."""
    query = create_query(
        flights=[
            FlightQuery(
                date=search["date"],
                from_airport=search["from"],
                to_airport=search["to"],
                max_stops=0,
            )
        ],
        currency=currency,
        language="tr",
    )
    results = get_flights(query)
    url = query.url()
    flights = []
    for r in results:
        if len(r.flights) != 1 or not r.price:
            continue  # sadece direkt ve fiyatı olan uçuşlar
        seg = r.flights[0]
        flights.append(
            Flight(
                leg=search["leg"],
                origin=search["from"],
                dest=search["to"],
                departure=_to_dt(seg.departure),
                arrival=_to_dt(seg.arrival),
                airline=", ".join(r.airlines),
                price=int(r.price),
                search_url=url,
                sources=(("Google", int(r.price)),),
            )
        )
    # Aynı uçuş birden fazla gelirse en ucuzunu tut
    unique: dict[str, Flight] = {}
    for f in flights:
        if f.key not in unique or f.price < unique[f.key].price:
            unique[f.key] = f
    return list(unique.values())
