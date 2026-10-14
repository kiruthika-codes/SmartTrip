
import math

from backend.places_service import PlacesService


class TransportService:
    """
    Hybrid transport estimator.

    Uses Geoapify for driving-route distance where possible.
    Uses clearly labelled prototype estimates for fares.
    Live ticket-pricing providers can be connected later.
    """

    # Prototype assumptions only; these are not live market prices.
    ESTIMATES = {
        "flight": {
            "rate_per_km": 5.0,
            "base_fare": 1200,
            "distance_factor": 1.0,
            "unit": "per traveller",
        },
        "train": {
            "rate_per_km": 1.5,
            "base_fare": 150,
            "distance_factor": 1.15,
            "unit": "per traveller",
        },
        "bus": {
            "rate_per_km": 2.0,
            "base_fare": 100,
            "distance_factor": 1.0,
            "unit": "per traveller",
        },
    }

    def __init__(self, places_service=None):
        self.places_service = places_service or PlacesService()

    @staticmethod
    def _haversine_km(start, end):
        """Calculate approximate straight-line distance between cities."""
        lat1 = math.radians(start["latitude"])
        lon1 = math.radians(start["longitude"])
        lat2 = math.radians(end["latitude"])
        lon2 = math.radians(end["longitude"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        return 6371 * 2 * math.asin(math.sqrt(a))

    def estimate_options(self, origin, destination, travellers=1):
        if travellers < 1:
            raise ValueError("Travellers must be at least 1.")

        start_parts = [part.strip() for part in origin.split(",", 1)]
        end_parts = [part.strip() for part in destination.split(",", 1)]

        if (
            len(start_parts) != 2
            or len(end_parts) != 2
            or not all(start_parts)
            or not all(end_parts)
        ):
            raise ValueError(
                "Use 'City, Country' for origin and destination."
            )

        start = self.places_service.get_city_coordinates(*start_parts)
        end = self.places_service.get_city_coordinates(*end_parts)

        straight_km = self._haversine_km(start, end)

        # Road distance is available only if Geoapify returns a route.
        road_km = None
        try:
            route = self.places_service.get_route(origin, destination)
            road_km = route["distance_meters"] / 1000
        except Exception:
            pass

        options = []

        for mode, assumptions in self.ESTIMATES.items():
            if mode == "flight":
                distance_km = straight_km
            elif mode == "train":
                # Approximation: rail routes may differ from straight lines.
                distance_km = straight_km * assumptions["distance_factor"]
            else:
                distance_km = (
                    road_km
                    if road_km is not None
                    else straight_km * 1.3
                )

            per_person = round(
                assumptions["base_fare"]
                + distance_km * assumptions["rate_per_km"]
            )

            options.append({
                "mode": mode,
                "distance_km_estimate": round(distance_km, 1),
                "estimated_one_way_per_person_inr": per_person,
                "estimated_one_way_total_inr": per_person * travellers,
                "travellers": travellers,
                "price_status": "estimated",
                "price_source": "Prototype formula; not a live fare",
                "notice": (
                    "Illustrative estimate only. Actual fares, availability, "
                    "route distance, class, taxes and fees may differ."
                ),
            })

        # Car: estimated fuel and tolls for one vehicle, not per person.
        if road_km is not None:
            fuel_cost = (road_km / 15) * 105
            toll_estimate = road_km * 1.5
            car_total = round(fuel_cost + toll_estimate)

            options.append({
                "mode": "car",
                "distance_km_estimate": round(road_km, 1),
                "estimated_one_way_per_person_inr": None,
                "estimated_one_way_total_inr": car_total,
                "travellers": travellers,
                "price_status": "estimated",
                "price_source": "Geoapify road distance + fuel/toll assumptions",
                "notice": (
                    "Assumes 15 km/l and fuel at ₹105/litre, plus an "
                    "approximate toll allowance. Excludes parking and rental."
                ),
            })

        return {
            "origin": origin,
            "destination": destination,
            "currency": "INR",
            "journey_type": "one_way",
            "options": options,
            "notice": (
                "No live ticket-pricing provider is connected yet. "
                "All prices returned by this prototype are estimates."
            ),
        }
