
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Activity:
    name: str
    time: str
    description: str
    estimated_cost_per_person: float = 0.0


@dataclass
class ItineraryDay:
    day_number: int
    title: str
    activities: list[Activity] = field(default_factory=list)


@dataclass
class TravelItinerary:
    destination: str
    duration_days: int
    travellers: int
    days: list[ItineraryDay] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the itinerary into JSON-friendly data."""
        return {
            "destination": self.destination,
            "duration_days": self.duration_days,
            "travellers": self.travellers,
            "days": [
                {
                    "day_number": day.day_number,
                    "title": day.title,
                    "activities": [
                        {
                            "name": activity.name,
                            "time": activity.time,
                            "description": activity.description,
                            "estimated_cost_per_person":
                                activity.estimated_cost_per_person,
                        }
                        for activity in day.activities
                    ],
                    "estimated_activity_cost_per_person": sum(
                        activity.estimated_cost_per_person
                        for activity in day.activities
                    ),
                }
                for day in self.days
            ],
        }



def normalize_activity_name(name: str) -> str:
    """Normalize an activity name for duplicate comparison."""
    return " ".join(str(name).casefold().split())

class ItineraryBuilder:
    """Builder pattern for constructing a travel itinerary."""

    def __init__(self):
        self.reset()

    
    def reset(self):
        self._destination = ""
        self._duration_days = 1
        self._travellers = 1
        self._days = []
        self._activity_names = set()
        return self


    def set_destination(self, destination: str):
        destination = destination.strip()
        if not destination:
            raise ValueError("Destination cannot be empty.")

        self._destination = destination
        return self

    def set_duration(self, duration_days: int):
        if not isinstance(duration_days, int) or duration_days < 1:
            raise ValueError("Duration must be a positive whole number.")

        self._duration_days = duration_days
        return self

    def set_travellers(self, travellers: int):
        if not isinstance(travellers, int) or travellers < 1:
            raise ValueError("Travellers must be at least one.")

        self._travellers = travellers
        return self

    
    def add_day(self, title: str, activities: list[Activity] | None = None):
        if len(self._days) >= self._duration_days:
            raise ValueError("The itinerary already has all its days.")

        unique_activities = []

        for activity in activities or []:
            key = normalize_activity_name(activity.name)

            if not key or key in self._activity_names:
                continue

            self._activity_names.add(key)
            unique_activities.append(activity)

        day = ItineraryDay(
            day_number=len(self._days) + 1,
            title=title,
            activities=unique_activities,
        )
        self._days.append(day)
        return self


    def build(self) -> TravelItinerary:
        if not self._destination:
            raise ValueError("Set a destination before building.")

        if len(self._days) != self._duration_days:
            raise ValueError(
                f"Expected {self._duration_days} days, "
                f"but only {len(self._days)} days were added."
            )

        itinerary = TravelItinerary(
            destination=self._destination,
            duration_days=self._duration_days,
            travellers=self._travellers,
            days=list(self._days),
        )

        return itinerary


if __name__ == "__main__":
    builder = ItineraryBuilder()

    itinerary = (
        builder
        .set_destination("Kyoto")
        .set_duration(3)
        .set_travellers(2)
        .add_day(
            "Culture and historic landmarks",
            [
                Activity(
                    name="Visit a historic temple",
                    time="09:00",
                    description="Explore local architecture and history.",
                    estimated_cost_per_person=10.0,
                ),
                Activity(
                    name="Explore a traditional market",
                    time="13:00",
                    description="Discover local food and crafts.",
                    estimated_cost_per_person=15.0,
                ),
            ],
        )
        .add_day(
            "Gardens and local culture",
            [
                Activity(
                    name="Visit a Japanese garden",
                    time="09:30",
                    description="Walk through a landscaped garden.",
                    estimated_cost_per_person=8.0,
                ),
            ],
        )
        .add_day(
            "Food and neighbourhood exploration",
            [
                Activity(
                    name="Local food experience",
                    time="11:00",
                    description="Try regional dishes.",
                    estimated_cost_per_person=20.0,
                ),
            ],
        )
        .build()
    )

    print("Sample itinerary:")
    print(itinerary.to_dict())
