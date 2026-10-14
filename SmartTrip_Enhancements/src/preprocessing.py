
from pathlib import Path
import ast
import pandas as pd


# --------------------------------------------------
# 1. DEFINE PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = (
    PROJECT_ROOT
    / "dataset"
    / "raw"
    / "Worldwide Travel Cities Dataset (Ratings and Climate).csv"
)

PROCESSED_FOLDER = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = (
    PROCESSED_FOLDER
    / "processed_travel_cities.csv"
)


# --------------------------------------------------
# 2. DEFINE DATASET FEATURES
# --------------------------------------------------

SCORE_COLUMNS = [
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

DURATION_OPTIONS = [
    "Day trip",
    "Weekend",
    "Short trip",
    "One week",
    "Long trip",
]


# --------------------------------------------------
# 3. PARSE THE IDEAL DURATIONS COLUMN
# --------------------------------------------------

def parse_durations(value):
    """Convert duration values into a clean list."""

    if pd.isna(value):
        return []

    if isinstance(value, (list, tuple, set)):
        items = list(value)

    else:
        text = str(value).strip()

        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, (list, tuple, set)):
                items = list(parsed)
            elif isinstance(parsed, str):
                items = [parsed]
            else:
                items = []

        except (ValueError, SyntaxError):
            # Fallback for comma-separated duration values.
            items = text.split(",")

    valid_options = {
        option.lower(): option
        for option in DURATION_OPTIONS
    }

    cleaned = []

    for item in items:
        label = str(item).strip()
        canonical_label = valid_options.get(label.lower())

        if canonical_label and canonical_label not in cleaned:
            cleaned.append(canonical_label)

    return cleaned


# --------------------------------------------------
# 4. LOAD THE DATASET
# --------------------------------------------------

def preprocess_dataset():

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_FILE}\n"
            "Place the original CSV inside data/raw/"
            " and name it worldwide_travel_cities.csv."
        )

    df = pd.read_csv(RAW_FILE)

    print("=" * 60)
    print("SMARTTRIP - DATASET INSPECTION")
    print("=" * 60)

    print("\nOriginal dataset shape:")
    print(df.shape)

    print("\nFirst five rows:")
    print(df.head())

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nDataset information:")
    df.info()


    # --------------------------------------------------
    # 5. STANDARDIZE COLUMN NAMES
    # --------------------------------------------------

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # Remove accidental whitespace from text values.
    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].map(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )


    # --------------------------------------------------
    # 6. VALIDATE REQUIRED COLUMNS
    # --------------------------------------------------

    required_columns = [
        "city",
        "country",
        "budget_level",
        "ideal_durations",
        *SCORE_COLUMNS,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            + ", ".join(missing_columns)
            + "\nCheck the CSV headers before continuing."
        )


    # --------------------------------------------------
    # 7. CHECK MISSING VALUES
    # --------------------------------------------------

    print("\nMissing values before cleaning:")
    print(df.isnull().sum())

    print(
        "\nTotal missing cells:",
        int(df.isnull().sum().sum())
    )


    # --------------------------------------------------
    # 8. REMOVE EXACT DUPLICATE RECORDS
    # --------------------------------------------------

    original_rows = len(df)

    exact_duplicates = int(df.duplicated().sum())

    df = df.drop_duplicates().copy()

    print("\nExact duplicate records found:", exact_duplicates)
    print("Exact duplicate records removed:", exact_duplicates)
    print("Rows remaining:", len(df))

    # City names alone are not unique identifiers.
    # For example, the same city name can exist
    # in different countries.
    duplicate_city_country = df.duplicated(
        subset=["city", "country"]
    ).sum()

    print(
        "Repeated city-country combinations:",
        int(duplicate_city_country)
    )

    print("Original row count:", original_rows)


    # --------------------------------------------------
    # 9. CONVERT NUMERIC COLUMNS
    # --------------------------------------------------

    numeric_columns = [
        "latitude",
        "longitude",
        *SCORE_COLUMNS,
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    print("\nPreference score validation:")

    for column in SCORE_COLUMNS:
        invalid_mask = (
            df[column].isna()
            | ~df[column].between(1, 5)
        )

        invalid_count = int(invalid_mask.sum())

        print(
            f"{column}: "
            f"minimum={df[column].min()}, "
            f"maximum={df[column].max()}, "
            f"invalid/missing={invalid_count}"
        )


    # --------------------------------------------------
    # 10. CLEAN DESCRIPTION VALUES
    # --------------------------------------------------

    df["short_description"] = (
        df["short_description"].fillna("")
        if "short_description" in df.columns
        else ""
    )


    # --------------------------------------------------
    # 11. PARSE TRIP DURATIONS
    # --------------------------------------------------

    duration_lists = df["ideal_durations"].apply(
        parse_durations
    )

    # Keep the duration information in readable text form.
    df["ideal_durations"] = duration_lists.apply(
        lambda values: ", ".join(values)
    )


    # --------------------------------------------------
    # 12. CREATE BINARY DURATION COLUMNS
    # --------------------------------------------------

    duration_column_names = {
        "Day trip": "day_trip",
        "Weekend": "weekend",
        "Short trip": "short_trip",
        "One week": "one_week",
        "Long trip": "long_trip",
    }

    for duration, column_name in duration_column_names.items():

        df[column_name] = duration_lists.apply(
            lambda values: int(duration in values)
        )

    print("\nDuration flags created:")
    print(
        df[
            list(duration_column_names.values())
        ].sum()
    )


    # --------------------------------------------------
    # 13. FINAL VALIDATION
    # --------------------------------------------------

    print("\nFinal dataset shape:")
    print(df.shape)

    print("\nMissing values after preprocessing:")
    print(df.isnull().sum())

    print("\nProcessed dataset preview:")
    preview_columns = [
        "city",
        "country",
        "budget_level",
        "ideal_durations",
        "day_trip",
        "weekend",
        "short_trip",
        "one_week",
        "long_trip",
    ]

    print(df[preview_columns].head(10))


    # --------------------------------------------------
    # 14. SAVE PROCESSED DATASET
    # --------------------------------------------------

    PROCESSED_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nPreprocessing completed successfully!")
    print("Saved processed dataset to:")
    print(OUTPUT_FILE)

    return df


# --------------------------------------------------
# 15. RUN THE PREPROCESSING SCRIPT
# --------------------------------------------------

if __name__ == "__main__":
    processed_df = preprocess_dataset()
