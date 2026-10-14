
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# .env is in the new_smartTrip project root.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

IGNAV_BASE_URL = "https://ignav.com/api"


async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    return_date: str | None = None,
    market: str = "IN",
):
    api_key = os.getenv("IGNAV_API_KEY")
    if not api_key:
        raise RuntimeError("IGNAV_API_KEY is missing from .env")

    if not 1 <= adults <= 9:
        raise ValueError(
            "Ignav supports at most 9 passengers per flight search. "
            "Larger groups need separate searches and confirmed group pricing."
        )

    if origin == destination:
        raise ValueError("Origin and destination must be different.")

    endpoint = (
        "/fares/round-trip" if return_date
        else "/fares/one-way"
    )

    payload = {
        "origin": origin.strip().upper(),
        "destination": destination.strip().upper(),
        "departure_date": departure_date,
        "adults": adults,
        "market": market.upper(),
    }

    if return_date:
        payload["return_date"] = return_date

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{IGNAV_BASE_URL}{endpoint}",
            headers={
                "X-Api-Key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.is_error:
        # Do not expose the API key or provider response details to users.
        raise RuntimeError(
            f"Ignav flight search failed (HTTP {response.status_code})."
        )

    data = response.json()
    results = []

    for item in data.get("itineraries", []):
        price = item.get("price") or {}
        outbound = item.get("outbound") or {}

        # Never present an unverified or zero placeholder as a real fare.
        if price.get("status") != "verified" or price.get("amount", 0) <= 0:
            continue

        results.append({
            "price": price["amount"],
            "currency": price.get("currency"),
            "price_status": price.get("status"),
            "airline": outbound.get("carrier"),
            "duration_minutes": outbound.get("duration_minutes"),
            "outbound": outbound,
            "inbound": item.get("inbound"),
            "ignav_id": item.get("ignav_id"),
        })

    return {
        "origin": data.get("origin", origin.upper()),
        "destination": data.get("destination", destination.upper()),
        "departure_date": data.get("departure_date", departure_date),
        "return_date": data.get("return_date", return_date),
        "observed_at": data.get("observed_at"),
        "cache_hit": data.get("cache_hit"),
        "itineraries": results,
        "source": "Ignav",
        "price_note": (
            "Provider-verified fare at search time; final price and "
            "availability must be confirmed at booking."
        ),
    }
