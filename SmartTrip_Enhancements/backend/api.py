
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.recommender import SmartTripRecommender
from backend.itinerary_builder import ItineraryBuilder, Activity
from backend.cost_calculator import TripExpenses, TravelCostCalculator
from backend.rag_retriever import RAGContextRetriever

from fastapi.middleware.cors import CORSMiddleware

from fastapi import HTTPException, Query
from backend.flight_service import search_flights

import airportsdata
from fastapi import HTTPException, Query

app = FastAPI(
    title="SmartTrip API",
    description="AI-Based Travel Planning and Recommendation System",
    version="1.0.0",
)


# Load the airport database once when the server starts.
IATA_AIRPORTS = airportsdata.load("IATA")


@app.get("/api/airports/resolve")
def resolve_airport(query: str = Query(..., min_length=2)):
    """Find an airport using its name, city, or IATA code."""

    search = query.strip().casefold()
    
    # Handle city names that differ from the airport database name.
    AIRPORT_ALIASES = {
        "suva": "SUV",
        "suva, fiji": "SUV",
        "nausori": "SUV",
    }

    if search in AIRPORT_ALIASES:
        alias_code = AIRPORT_ALIASES[search]

        if alias_code in IATA_AIRPORTS:
            airport = IATA_AIRPORTS[alias_code]
            return {
                "iata_code": alias_code,
                "city": "Suva",
                "airport_name": airport.get("name", "Nausori International Airport"),
                "country": airport.get("country", "Fiji"),
            }

    if not search:
        raise HTTPException(
            status_code=400,
            detail="Please enter a city or airport name."
        )

    # If the user already entered an IATA code, use it.
    code = search.upper()

    if len(code) == 3 and code in IATA_AIRPORTS:
        airport = IATA_AIRPORTS[code]
        return {
            "iata_code": airport["iata"],
            "city": airport.get("city", ""),
            "airport_name": airport.get("name", ""),
            "country": airport.get("country", "")
        }

    airports = list(IATA_AIRPORTS.values())

    # First look for an exact city name.
    matches = [
        airport for airport in airports
        if airport.get("city", "").casefold() == search
    ]

    # Next look for an exact airport name.
    if not matches:
        matches = [
            airport for airport in airports
            if airport.get("name", "").casefold() == search
        ]

    # Finally, try a partial match.
    if not matches:
        matches = [
            airport for airport in airports
            if search in airport.get("city", "").casefold()
            or search in airport.get("name", "").casefold()
        ]

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No airport found for '{query}'."
        )

    # Prefer an exact city match if one exists.
    airport = next(
        (
            item for item in matches
            if item.get("city", "").casefold() == search
        ),
        matches[0]
    )

    return {
        "iata_code": airport["iata"],
        "city": airport.get("city", ""),
        "airport_name": airport.get("name", ""),
        "country": airport.get("country", "")
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

recommender = SmartTripRecommender()
rag_retriever = RAGContextRetriever()
cost_calculator = TravelCostCalculator()


class InterestPreferences(BaseModel):
    culture: int = Field(default=3, ge=1, le=5)
    adventure: int = Field(default=3, ge=1, le=5)
    nature: int = Field(default=3, ge=1, le=5)
    beaches: int = Field(default=3, ge=1, le=5)
    nightlife: int = Field(default=3, ge=1, le=5)
    cuisine: int = Field(default=3, ge=1, le=5)
    wellness: int = Field(default=3, ge=1, le=5)
    urban: int = Field(default=3, ge=1, le=5)
    seclusion: int = Field(default=3, ge=1, le=5)



class RecommendationRequest(BaseModel):
    budget: Literal["Budget", "Mid-range", "Luxury"]
    duration: Literal[
        "Day trip", "Weekend", "Short trip", "One week", "Long trip"
    ]
    interests: InterestPreferences
    country_scope: Literal["india", "worldwide"] = "worldwide"
    top_k: int = Field(default=5, ge=1, le=20)



class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    top_k: int = Field(default=5, ge=1, le=20)


class ActivityInput(BaseModel):
    name: str = Field(min_length=1)
    time: str = "09:00"
    description: str = ""
    estimated_cost_per_person: float = Field(default=0, ge=0)


class DayInput(BaseModel):
    title: str = Field(min_length=1)
    activities: list[ActivityInput] = Field(default_factory=list)


class ItineraryRequest(BaseModel):
    destination: str = Field(min_length=1)
    duration_days: int = Field(ge=1, le=60)
    travellers: int = Field(default=1, ge=1, le=100)
    days: list[DayInput]


class CostRequest(BaseModel):
    budget: Literal["Budget", "Mid-range", "Luxury"] = "Mid-range"
    budget_limit: float | None = Field(default=None, ge=0)
    travellers: int = Field(ge=1, le=100)
    days: int = Field(ge=1, le=60)
    budget_limit: float | None = Field(default=None, ge=0)

    transport: float = Field(default=0, ge=0)
    accommodation_per_room_per_night: float = Field(default=0, ge=0)
    rooms: int = Field(default=1, ge=1, le=100)
    nights: int = Field(default=0, ge=0, le=60)
    food_per_person_per_day: float = Field(default=0, ge=0)
    local_transport_per_person_per_day: float = Field(default=0, ge=0)
    attraction_fees_per_person: float = Field(default=0, ge=0)
    activity_fees_per_person: float = Field(default=0, ge=0)


class RAGRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    top_k: int = Field(default=3, ge=1, le=10)


def json_safe_records(results):
    """Convert dataframe records into JSON-compatible values."""
    import math
    import pandas as pd

    records = results.to_dict(orient="records")
    safe_records = []

    for record in records:
        safe_record = {}

        for key, value in record.items():
            if pd.isna(value):
                value = None
            elif hasattr(value, "item"):
                value = value.item()

            if isinstance(value, float) and not math.isfinite(value):
                value = None

            safe_record[key] = value

        safe_records.append(safe_record)

    return safe_records


@app.get("/")
def home():
    return {
        "project": "SmartTrip",
        "message": "SmartTrip API is running!",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "destinations_loaded": len(recommender.get_destinations()),
    }


@app.post("/destinations/search")
def search_destinations(request: SearchRequest):
    try:
        results = recommender.recommend(
            "content",
            {"query": request.query},
            top_k=request.top_k,
        )

        return {
            "method": "content-based",
            "count": len(results),
            "destinations": json_safe_records(results),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Search failed: {exc}"
        ) from exc


@app.post("/destinations/recommend")
def recommend_destinations(request: RecommendationRequest):
    try:
        results = recommender.recommend(
            "category",
            {
                "budget": request.budget,
                "duration": request.duration,
                "country_scope": request.country_scope,
                "interests": request.interests.dict()
            },
            top_k=request.top_k,
        )

        return {
            "method": "category-based",
            "count": len(results),
            "destinations": json_safe_records(results),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Recommendation failed: {exc}"
        ) from exc


@app.post("/itinerary/build")
def build_itinerary(request: ItineraryRequest):
    if len(request.days) != request.duration_days:
        raise HTTPException(
            status_code=422,
            detail="The number of supplied day plans must equal duration_days.",
        )

    try:
        builder = (
            ItineraryBuilder()
            .set_destination(request.destination)
            .set_duration(request.duration_days)
            .set_travellers(request.travellers)
        )

        for day in request.days:
            activities = [
                Activity(
                    name=item.name,
                    time=item.time,
                    description=item.description,
                    estimated_cost_per_person=item.estimated_cost_per_person,
                )
                for item in day.activities
            ]
            builder.add_day(day.title, activities)

        itinerary = builder.build()
        return itinerary.to_dict()

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/cost/calculate")
def calculate_cost(request: CostRequest):
    """Return profile-based local estimates plus any user-entered transport costs."""
    try:
        from backend.budget_profiles import estimate_local_expenses
        local = estimate_local_expenses(
            level=request.budget,
            travellers=request.travellers,
            days=request.days,
        )
        transport = float(request.transport or 0)
        # Optional manual cost inputs override/add to the profile estimate.
        accommodation_extra = request.accommodation_per_room_per_night * request.rooms * request.nights
        food_extra = request.food_per_person_per_day * request.travellers * request.days
        local_transport_extra = request.local_transport_per_person_per_day * request.travellers * request.days
        attractions_extra = request.attraction_fees_per_person * request.travellers
        activities_extra = request.activity_fees_per_person * request.travellers
        total = round(local["estimated_local_expenses"] + transport + accommodation_extra + food_extra + local_transport_extra + attractions_extra + activities_extra, 2)
        # Manual category inputs are additional costs; disclose this to avoid implying live pricing.
        result = dict(local)
        result.update({
            "transport_cost": round(transport, 2),
            "estimated_transport_expenses": round(transport, 2),
            "estimated_accommodation_extra": round(accommodation_extra, 2),
            "estimated_food_extra": round(food_extra, 2),
            "estimated_local_transport_extra": round(local_transport_extra, 2),
            "estimated_attraction_fees": round(attractions_extra, 2),
            "estimated_activity_fees": round(activities_extra, 2),
            "estimated_total_trip_cost": total,
            "estimated_total_cost": total,
            "estimated_total_per_person": round(total / request.travellers, 2),
            "budget_limit": request.budget_limit,
            "budget_remaining": round(request.budget_limit - total, 2) if request.budget_limit is not None else None,
            "is_estimate": True,
            "price_note": "Planning estimate based on selected budget profile and any manual costs; not live booking prices.",
        })
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/rag/retrieve")
def retrieve_destination_context(request: RAGRequest):
    try:
        contexts = rag_retriever.retrieve(
            request.query,
            top_k=request.top_k,
        )

        return {
            "query": request.query,
            "count": len(contexts),
            "contexts": contexts,
            "generated_answer": None,
            "note": (
                "Retrieval only: no LLM-generated answer has been "
                "configured yet."
            ),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Retrieval failed: {exc}"
        ) from exc


from backend.planning_service import SmartTripPlanningService

planning_service = SmartTripPlanningService()


class TripRecommendationRequest(BaseModel):
    budget_level: str
    duration: str
    days: int
    travellers: int
    interests: dict[str, int]


@app.post("/trip/recommend")
def trip_recommend(request: TripRecommendationRequest):
    if request.days < 1 or request.travellers < 1:
        raise HTTPException(
            status_code=400,
            detail="Days and travellers must be at least 1"
        )

    try:
        destinations = planning_service.recommend_destinations(
            budget=request.budget_level,
            duration=request.duration,
            interests=request.interests,
            top_k=3,
        )

        expenses = planning_service.estimate_budget(
            budget=request.budget_level,
            travellers=request.travellers,
            days=request.days,
        )

        return {
            "destinations": json_safe_records(destinations),
            "budget_estimate": expenses,
            "message": (
                "Local expense estimates only. "
                "International transport and other travel costs "
                "are not included."
            ),
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


class TripItineraryRequest(BaseModel):
    destination: str
    budget_level: str
    days: int
    travellers: int
    interests: dict[str, int]


@app.post("/trip/itinerary")
def generate_trip_itinerary(request: TripItineraryRequest):
    if request.days < 1 or request.travellers < 1:
        raise HTTPException(
            status_code=400,
            detail="Days and travellers must be at least 1",
        )

    try:
        itinerary = planning_service.build_itinerary(
            destination=request.destination,
            days=request.days,
            travellers=request.travellers,
            interests=request.interests,
        )

        budget_estimate = planning_service.estimate_budget(
            budget=request.budget_level,
            travellers=request.travellers,
            days=request.days,
        )

        return {
            "itinerary": itinerary.to_dict(),
            "budget_estimate": budget_estimate,
            "notice": (
                "Activities are templates, not verified attractions. "
                "The budget is an estimate and excludes international "
                "transport and other expenses listed as excluded."
            ),
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/places/hotels")
def recommend_hotels(city: str, country: str, limit: int = 10):
    """Return nearby accommodation listings from Geoapify when available."""
    try:
        from backend.places_service import PlacesService
        service = PlacesService()
        location = service.get_city_coordinates(city, country)
        hotels = service.search_hotels(location["latitude"], location["longitude"], limit=limit)
        return {"destination": location, "count": len(hotels), "hotels": hotels, "price_note": "Live room prices and availability are not supplied by this endpoint; verify with the property."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Hotel search failed: {exc}") from exc


@app.get("/weather/forecast")
def weather_forecast(city: str, country: str):
    """Fetch a public Open-Meteo forecast for a city (no API key required)."""
    try:
        import httpx
        from backend.places_service import PlacesService
        location = PlacesService().get_city_coordinates(city, country)
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"], "longitude": location["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": 16, "timezone": "auto"
            }, timeout=15.0
        )
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily", {})
        forecasts = []
        for i, date in enumerate(daily.get("time", [])):
            rain = (daily.get("precipitation_probability_max") or [None] * len(daily.get("time", [])))[i]
            code = (daily.get("weather_code") or [None] * len(daily.get("time", [])))[i]
            advice = "Prefer indoor or flexible activities" if (rain is not None and rain >= 60) or code in [61,63,65,80,81,82,95,96,99] else "Outdoor activities may be suitable; check local conditions"
            forecasts.append({"date": date, "weather_code": code, "min_c": (daily.get("temperature_2m_min") or [None]*len(daily.get("time", [])))[i], "max_c": (daily.get("temperature_2m_max") or [None]*len(daily.get("time", [])))[i], "precipitation_probability": rain, "activity_advice": advice})
        return {"destination": location, "forecast": forecasts, "note": "Forecast availability is limited to the returned dates. Later trip dates need seasonal planning, not a live forecast."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather forecast failed: {exc}") from exc


@app.get("/api/flights/live")
async def live_flight_search(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    departure_date: str = Query(...),
    adults: int = Query(1, ge=1, le=9),
    return_date: str | None = Query(None),
):
    from datetime import date

    try:
        date.fromisoformat(departure_date)
        if return_date:
            date.fromisoformat(return_date)
            if return_date <= departure_date:
                raise ValueError("Return date must be after departure date.")

        return await search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            adults=adults,
            return_date=return_date,
            market="IN",
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        message = str(exc)
        status = 503 if "IGNAV_API_KEY" in message else 502
        raise HTTPException(status_code=status, detail=message)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve flight offers right now.",
        )
