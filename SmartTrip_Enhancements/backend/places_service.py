
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
GEOAPIFY_URL = "https://api.geoapify.com/v2/places"


class PlacesService:
    """Fetch nearby attractions using Geoapify."""

    
    def search_attractions(self, latitude, longitude, limit=20):
        """Find named attractions within a wider radius."""

        if not GEOAPIFY_API_KEY:
            raise RuntimeError(
                "GEOAPIFY_API_KEY is missing. Check the root .env file."
            )

        # Search within 15 km instead of 5 km.
        params = {
            "categories": (
                "tourism.attraction,"
                "tourism.sights,"
                "entertainment.museum,"
                "entertainment.culture,"
                "natural,"
                "leisure.park"
            ),
            "filter": f"circle:{longitude},{latitude},15000",
            "bias": f"proximity:{longitude},{latitude}",
            "limit": min(max(int(limit), 1), 20),
            "apiKey": GEOAPIFY_API_KEY,
        }

        try:
            response = httpx.get(
                GEOAPIFY_URL,
                params=params,
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise RuntimeError(
                f"Geoapify returned HTTP {error.response.status_code}. "
                "Check your API key, quota and request."
            ) from error
        except httpx.RequestError as error:
            raise RuntimeError(
                f"Could not connect to Geoapify: {error}"
            ) from error

        data = response.json()
        attractions = []
        seen_names = set()

        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            coordinates = feature.get("geometry", {}).get(
                "coordinates", []
            )
            categories = properties.get("categories", [])
            name = str(properties.get("name") or "").strip()

            if not name:
                continue

            # Deduplicate names, ignoring capitalization and whitespace.
            key = " ".join(name.casefold().split())
            if key in seen_names:
                continue
            seen_names.add(key)

            attractions.append({
                "name": name,
                "address": properties.get(
                    "formatted", "Address unavailable"
                ),
                "categories": categories,
                "latitude": (
                    coordinates[1] if len(coordinates) >= 2 else None
                ),
                "longitude": (
                    coordinates[0] if len(coordinates) >= 2 else None
                ),
            })

        return attractions

     
    def get_city_coordinates(self, city, country):
        """Find a destination's coordinates using Geoapify."""

        if not GEOAPIFY_API_KEY:
            raise RuntimeError(
                "GEOAPIFY_API_KEY is missing. Check the root .env file."
            )

        response = httpx.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={
                "text": f"{city}, {country}",
                "format": "json",
                "limit": 1,
                "apiKey": GEOAPIFY_API_KEY,
            },
            timeout=20.0,
        )
        response.raise_for_status()

        results = response.json().get("results", [])

        if not results:
            raise ValueError(
                f"Could not find coordinates for {city}, {country}"
            )

        place = results[0]

        return {
            "city": city,
            "country": country,
            "latitude": place["lat"],
            "longitude": place["lon"],
            "formatted_address": place.get(
                "formatted", f"{city}, {country}"
            ),
        }

    
    def search_city_attractions(self, city, country, limit=20):
        """Find a city, then search for nearby attractions."""

        location = self.get_city_coordinates(city, country)

        attractions = self.search_attractions(
            latitude=location["latitude"],
            longitude=location["longitude"],
            limit=limit,
        )

        return {
            "destination": location,
            "attractions": attractions,
            "count": len(attractions),
        }

    

    def search_hotels(self, latitude, longitude, limit=10):
        """Search accommodation listings near a destination; prices are not live."""
        if not GEOAPIFY_API_KEY:
            raise RuntimeError("GEOAPIFY_API_KEY is missing. Check the root .env file.")
        params = {
            "categories": "accommodation.hotel,accommodation.hostel,accommodation.guest_house,accommodation.motel",
            "filter": f"circle:{longitude},{latitude},15000",
            "bias": f"proximity:{longitude},{latitude}",
            "limit": min(max(int(limit), 1), 20),
            "apiKey": GEOAPIFY_API_KEY,
        }
        response = httpx.get(GEOAPIFY_URL, params=params, timeout=20.0)
        response.raise_for_status()
        hotels = []
        seen = set()
        for feature in response.json().get("features", []):
            props = feature.get("properties", {})
            name = str(props.get("name") or "").strip()
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            hotels.append({
                "name": name,
                "address": props.get("formatted", "Address unavailable"),
                "categories": props.get("categories", []),
                "website": props.get("website") or None,
                "latitude": (feature.get("geometry", {}).get("coordinates") or [None, None])[1],
                "longitude": (feature.get("geometry", {}).get("coordinates") or [None, None])[0],
                "price": None,
                "price_note": "Price and availability not provided by Geoapify; check the hotel's website.",
            })
        return hotels

    def get_route(self, origin, destination):
        """Estimate a driving route between two city names."""

        origin_parts = [part.strip() for part in origin.split(",", 1)]
        destination_parts = [
            part.strip() for part in destination.split(",", 1)
        ]

        if (
            len(origin_parts) != 2
            or len(destination_parts) != 2
            or not all(origin_parts)
            or not all(destination_parts)
        ):
            raise ValueError(
                "Use 'City, Country' for both origin and destination."
            )

        start = self.get_city_coordinates(*origin_parts)
        end = self.get_city_coordinates(*destination_parts)

        response = httpx.get(
            "https://api.geoapify.com/v1/routing",
            params={
                "waypoints": (
                    f"{start['latitude']},{start['longitude']}|"
                    f"{end['latitude']},{end['longitude']}"
                ),
                "mode": "drive",
                "apiKey": GEOAPIFY_API_KEY,
            },
            timeout=20.0,
        )
        response.raise_for_status()

        features = response.json().get("features", [])

        if not features:
            raise ValueError("No driving route was returned.")

        summary = features[0]["properties"]["distance"]
        return {
            "origin": start,
            "destination": end,
            "mode": "drive",
            "distance_meters": summary,
            "notice": (
                "Driving route estimate only. This does not represent "
                "international flight distance, time or cost."
            ),
        }
