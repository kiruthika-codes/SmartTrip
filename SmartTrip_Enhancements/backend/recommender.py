
from src.data_manager import TravelDataManager
from backend.factory import RecommendationFactory


class SmartTripRecommender:
    """Coordinates SmartTrip recommendation strategies."""

    def __init__(self, data_manager=None):
        self.data_manager = data_manager or TravelDataManager()

    def recommend(self, strategy_name, user_input, top_k=5):
        strategy = RecommendationFactory.create_strategy(
            strategy_name,
            self.data_manager,
        )

        return strategy.recommend(user_input, top_k=top_k)

    def get_destinations(self):
        return self.data_manager.get_data()
