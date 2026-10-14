
from pathlib import Path
import math
import re
from collections import Counter

import pandas as pd


class TravelDataManager:
    """Singleton that loads the processed travel dataset
    and provides pure-Python TF-IDF search.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        project_root = Path(__file__).resolve().parents[1]
        self.csv_path = (
            project_root
            / "data"
            / "processed"
            / "processed_travel_cities.csv"
        )

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Processed dataset not found: {self.csv_path}\n"
                "Run src/preprocessing.py first."
            )

        self.df = pd.read_csv(self.csv_path)

        text_columns = [
            "city",
            "country",
            "region",
            "short_description",
            "budget_level",
            "ideal_durations",
        ]

        self.text_columns = [
            col for col in text_columns if col in self.df.columns
        ]

        self.documents = []
        for _, row in self.df.iterrows():
            parts = [
                str(row[col])
                for col in self.text_columns
                if pd.notna(row[col])
            ]
            self.documents.append(" ".join(parts))

        self.document_vectors = []
        self.idf = {}
        self._build_index()
        self._initialized = True

    @staticmethod
    def tokenize(text):
        return re.findall(r"[a-z0-9]+", str(text).lower())

    def _build_index(self):
        token_lists = [
            self.tokenize(document)
            for document in self.documents
        ]

        document_frequency = Counter()
        term_counts = []

        for tokens in token_lists:
            counts = Counter(tokens)
            term_counts.append(counts)
            document_frequency.update(set(tokens))

        total_documents = len(self.documents)

        for term, count in document_frequency.items():
            self.idf[term] = (
                math.log((1 + total_documents) / (1 + count)) + 1
            )

        for counts in term_counts:
            vector = {
                term: frequency * self.idf[term]
                for term, frequency in counts.items()
            }

            norm = math.sqrt(sum(value ** 2 for value in vector.values()))

            if norm:
                vector = {
                    term: value / norm
                    for term, value in vector.items()
                }

            self.document_vectors.append(vector)

    
    def search(self, query, top_k=5):
        """Search destinations by exact text matches first, then TF-IDF."""

        query = str(query).strip()

        if not query:
            return self.df.head(0).copy().assign(
                similarity_score=pd.Series(dtype=float)
            )

        query_lower = query.casefold()
        limit = max(0, int(top_k))

        if limit == 0:
            return self.df.head(0).copy().assign(
                similarity_score=pd.Series(dtype=float)
            )

        # Prioritize direct matches in city, country, region and descriptions.
        searchable_columns = [
            column for column in [
                "city",
                "country",
                "region",
                "short_description",
                "description",
            ]
            if column in self.df.columns
        ]

        if searchable_columns:
            exact_mask = pd.Series(False, index=self.df.index)

            for column in searchable_columns:
                exact_mask |= (
                    self.df[column]
                    .fillna("")
                    .astype(str)
                    .str.contains(
                        re.escape(query),
                        case=False,
                        regex=True,
                        na=False,
                    )
                )

            exact_results = self.df.loc[exact_mask].copy()

            if not exact_results.empty:
                exact_results["similarity_score"] = 1.0
                return exact_results.head(limit).reset_index(drop=True)

        # Fall back to TF-IDF for broader text searches.
        query_counts = Counter(self.tokenize(query))

        query_vector = {
            term: frequency * self.idf[term]
            for term, frequency in query_counts.items()
            if term in self.idf
        }

        norm = math.sqrt(
            sum(value ** 2 for value in query_vector.values())
        )

        if not norm:
            return self.df.head(0).copy().assign(
                similarity_score=pd.Series(dtype=float)
            )

        query_vector = {
            term: value / norm
            for term, value in query_vector.items()
        }

        scores = []

        for index, document_vector in enumerate(self.document_vectors):
            score = sum(
                value * document_vector.get(term, 0.0)
                for term, value in query_vector.items()
            )

            if score > 0:
                scores.append((index, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        selected = scores[:limit]

        results = self.df.iloc[
            [index for index, _ in selected]
        ].copy()

        results["similarity_score"] = [
            score for _, score in selected
        ]

        return results.reset_index(drop=True)


    def get_data(self):
        return self.df.copy()


if __name__ == "__main__":
    manager = TravelDataManager()

    print("Dataset loaded:", manager.df.shape)
    print("\nTop destinations for your search:")

    results = manager.search(
        "historic temples vibrant street food nightlife",
        top_k=5,
    )

    columns = [
        col for col in
        ["city", "country", "similarity_score"]
        if col in results.columns
    ]

    print(results[columns].to_string(index=False))
