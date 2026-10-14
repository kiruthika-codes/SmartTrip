
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TripExpenses:
    # Transport costs for the whole group, including return travel.
    transport: float = 0.0

    # Accommodation price per room per night.
    accommodation_per_room_per_night: float = 0.0
    rooms: int = 1
    nights: int = 0

    # Food budget per person per day.
    food_per_person_per_day: float = 0.0

    # Local transport budget per person per day.
    local_transport_per_person_per_day: float = 0.0

    # Attraction and activity fees per person for the entire trip.
    attraction_fees_per_person: float = 0.0
    activity_fees_per_person: float = 0.0


class TravelCostCalculator:
    """Calculate estimated travel costs and validate the budget."""

    @staticmethod
    def _validate_non_negative(**values):
        for name, value in values.items():
            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative."
                )

    def calculate(
        self,
        expenses: TripExpenses,
        travellers: int,
        days: int,
        budget_limit: Optional[float] = None,
    ) -> dict:
        if travellers < 1:
            raise ValueError("Travellers must be at least one.")

        if days < 1:
            raise ValueError("Trip duration must be at least one day.")

        if expenses.rooms < 1:
            raise ValueError("At least one room must be selected.")

        if expenses.nights < 0:
            raise ValueError("Nights cannot be negative.")

        if expenses.nights > days:
            raise ValueError(
                "Nights cannot exceed the number of trip days."
            )

        if budget_limit is not None and budget_limit < 0:
            raise ValueError("Budget limit cannot be negative.")

        self._validate_non_negative(
            transport=expenses.transport,
            accommodation=expenses.accommodation_per_room_per_night,
            food=expenses.food_per_person_per_day,
            local_transport=expenses.local_transport_per_person_per_day,
            attraction_fees=expenses.attraction_fees_per_person,
            activity_fees=expenses.activity_fees_per_person,
        )

        breakdown = {
            "transport": expenses.transport,
            "accommodation": (
                expenses.accommodation_per_room_per_night
                * expenses.rooms
                * expenses.nights
            ),
            "food": expenses.food_per_person_per_day * travellers * days,
            "local_transport": (
                expenses.local_transport_per_person_per_day
                * travellers
                * days
            ),
            "attraction_fees": (
                expenses.attraction_fees_per_person * travellers
            ),
            "activity_fees": (
                expenses.activity_fees_per_person * travellers
            ),
        }

        total = round(sum(breakdown.values()), 2)
        per_person = round(total / travellers, 2)

        within_budget = (
            None
            if budget_limit is None
            else total <= budget_limit
        )

        remaining = (
            None
            if budget_limit is None
            else round(budget_limit - total, 2)
        )

        return {
            "currency": "INR",
            "travellers": travellers,
            "days": days,
            "nights": expenses.nights,
            "expense_breakdown": {
                name: round(amount, 2)
                for name, amount in breakdown.items()
            },
            "estimated_total": total,
            "estimated_cost_per_person": per_person,
            "budget_limit": budget_limit,
            "within_budget": within_budget,
            "remaining_budget": remaining,
            "note": (
                "Estimates only. Replace sample inputs with verified "
                "prices for the destination and travel dates."
            ),
        }


if __name__ == "__main__":
    calculator = TravelCostCalculator()

    sample_expenses = TripExpenses(
        transport=12000,
        accommodation_per_room_per_night=2500,
        rooms=1,
        nights=3,
        food_per_person_per_day=800,
        local_transport_per_person_per_day=300,
        attraction_fees_per_person=1000,
        activity_fees_per_person=1500,
    )

    result = calculator.calculate(
        expenses=sample_expenses,
        travellers=2,
        days=4,
        budget_limit=30000,
    )

    print("SmartTrip Cost Estimate")
    print("-----------------------")

    for category, amount in result["expense_breakdown"].items():
        print(f"{category.replace('_', ' ').title()}: ₹{amount:,.2f}")

    print(f"\nEstimated total: ₹{result['estimated_total']:,.2f}")
    print(
        "Cost per person: "
        f"₹{result['estimated_cost_per_person']:,.2f}"
    )
    print(f"Within budget: {result['within_budget']}")
    print(f"Remaining budget: ₹{result['remaining_budget']:,.2f}")
    print(result["note"])
