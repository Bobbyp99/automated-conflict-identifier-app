import pandas as pd
import re
from pathlib import Path


def normalize_text(text: str) -> str:
    """
    Lowercase text, remove punctuation, and collapse repeated spaces.
    """
    if pd.isna(text):
        return ""

    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_data():
    project_root = Path(__file__).resolve().parent.parent.parent
    decisions_path = project_root / "backend" / "decisions.csv"
    income_path = project_root / "backend" / "income_sources.csv"

    decisions_df = pd.read_csv(decisions_path)
    income_df = pd.read_csv(income_path)

    return decisions_df, income_df


def prepare_data(decisions_df: pd.DataFrame, income_df: pd.DataFrame):
    decisions_df["match_text_normalized"] = decisions_df["match_text"].apply(normalize_text)
    income_df["income_source_normalized"] = income_df["income_source"].apply(normalize_text)

    decisions_df["jurisdiction_normalized"] = (
        decisions_df["jurisdiction"].astype(str).str.strip().str.lower()
    )
    income_df["jurisdiction_normalized"] = (
        income_df["jurisdiction"].astype(str).str.strip().str.lower()
    )

    return decisions_df, income_df


def find_matches(decisions_df: pd.DataFrame, income_df: pd.DataFrame):
    matches = []

    for _, decision in decisions_df.iterrows():
        decision_jurisdiction = decision["jurisdiction_normalized"]
        decision_text = decision["match_text_normalized"]

        if not decision_text:
            continue

        for _, income_row in income_df.iterrows():
            official_jurisdiction = income_row["jurisdiction_normalized"]
            income_source = income_row["income_source_normalized"]

            if not income_source:
                continue

            if decision_jurisdiction != official_jurisdiction:
                continue

            if income_source in decision_text:
                matches.append({
                    "jurisdiction": decision["jurisdiction"],
                    "decision_title": decision["title"],
                    "decision_date": decision["date"],
                    "file_link": decision["file_link"],
                    "official_name": income_row["official_name"],
                    "income_source": income_row["income_source"],
                    "match_type": "substring",
                })

    return pd.DataFrame(matches)


def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    output_path = project_root / "backend" / "conflict_matches.csv"

    decisions_df, income_df = load_data()
    decisions_df, income_df = prepare_data(decisions_df, income_df)
    matches_df = find_matches(decisions_df, income_df)

    if matches_df.empty:
        print("No matches found.")
    else:
        print(matches_df)
        matches_df.to_csv(output_path, index=False)
        print(f"Saved matches to {output_path}")


if __name__ == "__main__":
    main()