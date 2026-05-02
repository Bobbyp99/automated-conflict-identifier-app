import pandas as pd
import re
from pathlib import Path


def extract_date(date_str: str) -> str:
    """
    Extract MM/DD/YYYY from strings like:
    'Date created 1/14/2021 5:23:43 PM'
    and convert it to YYYY-MM-DD.
    """
    if pd.isna(date_str):
        return ""

    date_str = str(date_str)
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", date_str)

    if not match:
        return ""

    parsed = pd.to_datetime(match.group(1), format="%m/%d/%Y", errors="coerce")
    if pd.isna(parsed):
        return ""

    return parsed.strftime("%Y-%m-%d")


def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    input_csv = project_root / "backend" / "scraped_data.csv"
    output_csv = project_root / "backend" / "decisions.csv"

    df = pd.read_csv(input_csv)

    decisions_df = pd.DataFrame(index=df.index)

    decisions_df["jurisdiction"] = "Santa Ana"

    decisions_df["title"] = (
        df["File Name"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+Document$", "", regex=True)
        .str.strip()
    )

    decisions_df["match_text"] = decisions_df["title"]
    decisions_df["date"] = df["Date Created"].apply(extract_date)
    decisions_df["file_link"] = df["File Link"].fillna("").astype(str).str.strip()

    decisions_df = decisions_df[decisions_df["title"] != ""]
    decisions_df = decisions_df.drop_duplicates(subset=["file_link"])

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    decisions_df.to_csv(output_csv, index=False)

    print(f"Created {output_csv}")
    print(decisions_df.head())


if __name__ == "__main__":
    main()