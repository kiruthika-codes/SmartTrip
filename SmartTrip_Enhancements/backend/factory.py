
from src.recommendation_strategies import (
    CategoryPreferenceStrategy,
    ContentBasedStrategy,
)


class RecommendationFactory:
    """Factory Method for creating recommendation strategies."""

    @staticmethod
    def create_strategy(strategy_name, data_manager=None):
        strategy_name = strategy_name.strip().lower()

        if strategy_name in ("category", "category-based"):
            return CategoryPreferenceStrategy(data_manager)

        if strategy_name in ("content", "content-based"):
            return ContentBasedStrategy(data_manager)

        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            "Choose 'category' or 'content'."
        )
