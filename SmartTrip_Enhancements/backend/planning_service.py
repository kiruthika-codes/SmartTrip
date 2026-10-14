
from backend.recommender import SmartTripRecommender
from backend.budget_profiles import estimate_local_expenses
from backend.itinerary_builder import ItineraryBuilder, Activity
from backend.places_service import PlacesService

class SmartTripPlanningService:
    """Coordinates recommendations, itinerary planning and budget estimates."""

    def __init__(self):
        self.recommender = SmartTripRecommender()
        self.places_service = PlacesService()

    def recommend_destinations(
        self,
        budget,
        duration,
        interests,
        top_k=3,
    ):
        preferences = {
            "budget": budget,
            "duration": duration,
            "interests": interests,
        }

        return self.recommender.recommend(
            strategy_name="category",
            user_input=preferences,
            top_k=top_k,
        )

    
    def estimate_budget(
            self,
            budget,
            travellers,
            days,
            origin=None,
            destination=None,
            transport_mode=None,
            round_trip=False,
        ):
        # Existing accommodation, food, local transport and activities.
        local = estimate_local_expenses(
            level=budget,
            travellers=travellers,
            days=days,
        )

        result = dict(local)
        result["transport"] = None
        result["transport_mode"] = transport_mode
        result["transport_cost"] = 0
        result["transport_price_status"] = "not_selected"

        if origin and destination and transport_mode:
            from backend.transport_service import TransportService

            transport_service = TransportService()
            transport_result = transport_service.estimate_options(
                origin=origin,
                destination=destination,
                travellers=travellers,
            )

            selected = next(
                (
                    option
                    for option in transport_result["options"]
                    if option["mode"] == transport_mode.lower()
                ),
                None,
            )

            if selected is None:
                raise ValueError(
                    "Transport mode must be flight, train, bus or car."
                )

            multiplier = 2 if round_trip else 1
            transport_cost = (
                selected["estimated_one_way_total_inr"] * multiplier
            )

            result["transport"] = selected
            result["transport_cost"] = transport_cost
            result["transport_price_status"] = selected["price_status"]

        local_total = local["estimated_local_expenses"]
        transport_cost = result["transport_cost"]
        total = local_total + transport_cost

        result["estimated_transport_expenses"] = transport_cost
        result["estimated_total_trip_cost"] = total
        result["estimated_total_per_person"] = round(
            total / travellers, 2
        )
        result["excludes"] = list(local["excludes"])
        if transport_cost:
            result["excludes"] = [
                item for item in result["excludes"]
                if item != "Flights and intercity transport"
            ]
        result["is_estimate"] = True

        return result


    def build_itinerary(self, destination, days, travellers, interests):
        """Build an itinerary with unique attractions across all days."""

        if days < 1 or travellers < 1:
            raise ValueError("Days and travellers must be at least 1.")

        parts = [part.strip() for part in destination.split(",", 1)]
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                "Enter the destination as 'City, Country', "
                "for example 'Porto, Portugal'."
            )

        city, country = parts

        # Request more attractions for longer trips.
        requested_limit = min(max(days * 6, 20), 100)

        result = self.places_service.search_city_attractions(
            city, country, limit=requested_limit
        )
        attractions = result.get("attractions", [])

        # Remove duplicate names.
        unique_attractions = []
        seen_names = set()

        for place in attractions:
            name = str(place.get("name", "")).strip()
            key = " ".join(name.casefold().split())

            if name and key not in seen_names:
                seen_names.add(key)
                unique_attractions.append(place)

        if not unique_attractions:
            raise ValueError(
                f"No matching attractions found for {destination}. "
                "Try another destination."
            )

        builder = ItineraryBuilder()
        builder.set_destination(destination)
        builder.set_duration(days)
        builder.set_travellers(travellers)

        slots = [
            ("09:00", "Morning visit"),
            ("13:00", "Afternoon visit"),
            ("17:00", "Evening visit"),
        ]

        # Never cycle through the list: each attraction is used only once.
        place_index = 0

        for day_number in range(1, days + 1):
            activities = []

            for time, label in slots:
                if place_index >= len(unique_attractions):
                    break

                place = unique_attractions[place_index]
                place_index += 1

                activities.append(
                    Activity(
                        name=place["name"].strip(),
                        time=time,
                        description=(
                            f"{label}. Place listed by Geoapify: "
                            f"{place.get('address') or 'Address unavailable'}. "
                            "Verify opening hours, travel time and access "
                            "before visiting."
                        ),
                    )
                )

            builder.add_day(f"Day {day_number}", activities)

        return builder.build()
