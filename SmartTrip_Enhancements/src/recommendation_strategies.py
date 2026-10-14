try:
    from src.data_manager import TravelDataManager
except ModuleNotFoundError:
    from data_manager import TravelDataManager

import pandas as pd

INTEREST_COLUMNS = [
    "culture",
    "adventure",
    "nature",
    "beaches",
    "nightlife",
    "cuisine",
    "wellness",
    "urban",
    "seclusion",
]

DURATION_FLAGS = {
    "Day trip": "day_trip",
    "Weekend": "weekend",
    "Short trip": "short_trip",
    "One week": "one_week",
    "Long trip": "long_trip",
}


class RecommendationStrategy:
    """Base class for the Strategy design pattern."""

    def recommend(self, user_input, top_k=5):
        raise NotImplementedError(
            "Subclasses must implement recommend()."
        )


class CategoryPreferenceStrategy(RecommendationStrategy):
    """Recommend destinations using budget, duration, and interests."""

    def __init__(self, data_manager=None):
        self.data_manager = data_manager or TravelDataManager()

    def recommend(self, user_input, top_k=5):
        df = self.data_manager.get_data().copy()

        

        budget = user_input.get("budget")
        duration = user_input.get("duration")
        country_scope = user_input.get("country_scope", "worldwide")
        preferences = user_input.get("interests", {})

        
        
        # Filter by country before applying budget, duration, and ranking.
        if country_scope == "india" and "country" in df.columns:
            df = df[
                df["country"]
                .astype(str)
                .str.strip()
                .str.casefold()
                .isin(["india", "republic of india"])
            ]


        # 1. Filter by budget.
        if budget and "budget_level" in df.columns:
            df = df[
                df["budget_level"].astype(str).str.casefold()
                == str(budget).casefold()
            ]

        # 2. Filter by trip duration.
        if duration:
            flag = DURATION_FLAGS.get(duration)

            if flag and flag in df.columns:
                df = df[df[flag].fillna(False).astype(bool)]
            elif "ideal_durations" in df.columns:
                df = df[
                    df["ideal_durations"]
                    .fillna("")
                    .astype(str)
                    .str.contains(duration, case=False, regex=False)
                ]

        if df.empty:
            return df.assign(match_score=pd.Series(dtype=float))

        # 3. Validate interest ratings and calculate match distance.
        valid_preferences = {
            name: float(value)
            for name, value in preferences.items()
            if name in INTEREST_COLUMNS
            and name in df.columns
            and isinstance(value, (int, float))
            and 1 <= value <= 5
        }

        if not valid_preferences:
            df["match_score"] = 0.0
            return df.head(top_k).reset_index(drop=True)

        distances = []

        for _, row in df.iterrows():
            differences = [
                abs(float(row[name]) - rating)
                for name, rating in valid_preferences.items()
                if pd_value_is_number(row[name])
            ]

            distances.append(
                sum(differences) / len(differences)
                if differences else float("inf")
            )

        df["match_score"] = distances

        # Lower distance means a closer match.
        return (
            df.sort_values("match_score", ascending=True)
            .head(top_k)
            .reset_index(drop=True)
        )


class ContentBasedStrategy(RecommendationStrategy):
    """Recommend destinations using a text query."""

    def __init__(self, data_manager=None):
        self.data_manager = data_manager or TravelDataManager()

    def recommend(self, user_input, top_k=5):
        query = user_input.get("query", "")

        if not query.strip():
            raise ValueError("Please provide a search query.")

        return self.data_manager.search(query, top_k=top_k)


def pd_value_is_number(value):
    try:
        number = float(value)
        return number == number  # Excludes NaN.
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    manager = TravelDataManager()

    strategy = CategoryPreferenceStrategy(manager)

    preferences = {
        "culture": 5,
        "adventure": 3,
        "nature": 4,
        "beaches": 2,
        "nightlife": 4,
        "cuisine": 5,
        "wellness": 2,
        "urban": 4,
        "seclusion": 1,
    }

    user_input = {
        "budget": "Mid-range",
        "duration": "One week",
        "interests": preferences,
    }

    results = strategy.recommend(user_input, top_k=5)

    display_columns = [
        column for column in [
            "city",
            "country",
            "budget_level",
            "match_score",
        ]
        if column in results.columns
    ]

    if results.empty:
        print("No destinations match those filters.")
        print("Try a different budget or trip duration.")
    else:
        print("\nRecommended destinations:\n")
        print(results[display_columns].to_string(index=False))
