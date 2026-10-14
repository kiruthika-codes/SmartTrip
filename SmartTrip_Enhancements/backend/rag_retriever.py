
from src.data_manager import TravelDataManager


class RAGContextRetriever:
    """Retrieve destination information to ground AI responses."""

    def __init__(self, data_manager=None):
        self.data_manager = data_manager or TravelDataManager()

    def retrieve(self, query, top_k=3):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Please provide a search query.")

        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        results = self.data_manager.search(
            query.strip(),
            top_k=top_k,
        )

        contexts = []

        for _, row in results.iterrows():
            context = {
                "city": str(row.get("city", "")),
                "country": str(row.get("country", "")),
                "region": str(row.get("region", "")),
                "description": str(
                    row.get("short_description", "")
                ),
                "budget_level": str(row.get("budget_level", "")),
                "ideal_durations": str(
                    row.get("ideal_durations", "")
                ),
                "similarity_score": float(
                    row.get("similarity_score", 0.0)
                ),
            }

            contexts.append(context)

        return contexts

    def build_context(self, query, top_k=3):
        """Format retrieved records as context for a future LLM."""
        contexts = self.retrieve(query, top_k=top_k)

        if not contexts:
            return "No relevant destination information was found."

        sections = []

        for item in contexts:
            sections.append(
                f"Destination: {item['city']}, {item['country']}\n"
                f"Region: {item['region']}\n"
                f"Description: {item['description']}\n"
                f"Budget level: {item['budget_level']}\n"
                f"Ideal durations: {item['ideal_durations']}\n"
                f"Retrieval similarity: "
                f"{item['similarity_score']:.3f}"
            )

        return "\n\n".join(sections)


if __name__ == "__main__":
    retriever = RAGContextRetriever()

    query = "historic temples vibrant street food nightlife"

    print("RAG retrieval test")
    print("==================")
    print(retriever.build_context(query, top_k=3))
