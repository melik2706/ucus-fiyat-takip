"""Kiwi.com'dan (Google'dan bağımsız ikinci kaynak) direkt uçuş fiyatlarını çeker.

Kiwi'nin web sitesinin kullandığı herkese açık GraphQL uç noktası; anahtar gerekmez.
Kiwi fiyatlarına Kiwi'nin kendi hizmet bedeli dahildir.
"""
from datetime import datetime

from primp import Client

from .models import Flight

KIWI_URL = "https://api.skypicker.com/umbrella/v2/graphql?featureName=SearchOneWayItinerariesQuery"
QUERY = """query SearchOneWayItinerariesQuery($search: SearchOnewayInput, $filter: ItinerariesFilterInput,
  $options: ItinerariesOptionsInput) {
 onewayItineraries(search: $search, filter: $filter, options: $options) {
  __typename
  ... on AppError { error: message }
  ... on Itineraries { itineraries { __typename ... on ItineraryOneWay {
     price { amount }
     sector { sectorSegments { segment {
       source { localTime station { code } }
       destination { localTime station { code } }
       carrier { name code } } } } } } }
 } }"""


def _variables(search: dict, currency: str) -> dict:
    day = search["date"]
    return {
        "search": {
            "itinerary": {
                "source": {"ids": [f"Station:airport:{search['from']}"]},
                "destination": {"ids": [f"Station:airport:{search['to']}"]},
                "outboundDepartureDate": {"start": f"{day}T00:00:00", "end": f"{day}T23:59:59"},
            },
            "passengers": {"adults": 1, "children": 0, "infants": 0, "adultsHoldBags": [0], "adultsHandBags": [0]},
            "cabinClass": {"cabinClass": "ECONOMY", "applyMixedClasses": False},
        },
        "filter": {"maxStopsCount": 0, "transportTypes": ["FLIGHT"], "limit": 30},
        "options": {"currency": currency.lower(), "locale": "tr", "partner": "skypicker",
                    "sortBy": "PRICE", "sortOrder": "ASCENDING"},
    }


def fetch_search(search: dict, currency: str) -> list[Flight]:
    client = Client(impersonate="chrome_145", impersonate_os="windows")
    resp = client.post(
        KIWI_URL,
        json={"query": QUERY, "variables": _variables(search, currency)},
        headers={"content-type": "application/json", "origin": "https://www.kiwi.com"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Kiwi HTTP {resp.status_code}")
    result = (resp.json().get("data") or {}).get("onewayItineraries") or {}
    if result.get("__typename") != "Itineraries":
        raise RuntimeError(f"Kiwi hata: {result.get('error') or result}")

    flights: list[Flight] = []
    for it in result.get("itineraries", []):
        segments = (it.get("sector") or {}).get("sectorSegments") or []
        if len(segments) != 1 or not it.get("price"):
            continue  # sadece direkt uçuşlar
        seg = segments[0]["segment"]
        price = int(round(float(it["price"]["amount"])))
        flights.append(
            Flight(
                leg=search["leg"],
                origin=search["from"],
                dest=search["to"],
                departure=datetime.fromisoformat(seg["source"]["localTime"]),
                arrival=datetime.fromisoformat(seg["destination"]["localTime"]),
                airline=seg["carrier"]["name"],
                price=price,
                sources=(("Kiwi", price),),
            )
        )
    return flights
