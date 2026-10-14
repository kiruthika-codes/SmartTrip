
BUDGET_PROFILES = {
    "Budget": {
        "daily_allowance": 2500,
        "accommodation_share": 0.40,
        "food_share": 0.30,
        "local_transport_share": 0.15,
        "activities_share": 0.15,
    },
    "Mid-range": {
        "daily_allowance": 6000,
        "accommodation_share": 0.40,
        "food_share": 0.30,
        "local_transport_share": 0.15,
        "activities_share": 0.15,
    },
    "Luxury": {
        "daily_allowance": 15000,
        "accommodation_share": 0.45,
        "food_share": 0.25,
        "local_transport_share": 0.10,
        "activities_share": 0.20,
    },
}


def get_budget_profile(level):
    if level not in BUDGET_PROFILES:
        raise ValueError(
            f"Unknown budget level: {level}. "
            f"Choose from {list(BUDGET_PROFILES)}"
        )

    return BUDGET_PROFILES[level]



def estimate_local_expenses(level, travellers, days):
    if travellers < 1 or days < 1:
        raise ValueError("Travellers and days must be at least 1.")

    profile = get_budget_profile(level)

    daily_allowance = profile["daily_allowance"]
    trip_multiplier = travellers * days
    total = daily_allowance * trip_multiplier

    accommodation = (
        total * profile["accommodation_share"]
    )
    food = total * profile["food_share"]
    local_transport = (
        total * profile["local_transport_share"]
    )
    activities = total * profile["activities_share"]

    return {
        "currency": "INR",
        "budget_level": level,
        "travellers": travellers,
        "days": days,
        "daily_allowance_per_person": daily_allowance,
        "estimated_accommodation": round(accommodation, 2),
        "estimated_food": round(food, 2),
        "estimated_local_transport": round(local_transport, 2),
        "estimated_activities": round(activities, 2),
        "estimated_local_expenses": round(total, 2),
        "per_person": round(total / travellers, 2),
        "includes": [
            "Accommodation",
            "Food",
            "Local transportation",
            "Activities",
        ],
        "excludes": [
            "Flights and intercity transport",
            "Visa fees",
            "Travel insurance",
        ],
        "is_estimate": True,
    }

