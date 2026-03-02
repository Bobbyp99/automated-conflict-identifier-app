import sys

# install pandas
# install openpyxl for reading excel files
import pandas as pd


from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).parents[1]))
from database import engine


def ingest_officials_data(sheets):
    all_officials = []

    jurisdiction_df = pd.read_sql(text("SELECT id, jurisdiction_name FROM jurisdictions"), con=engine)

    for sheet_name, sheet_data in sheets.items():
        if "First Name" not in sheet_data.columns or "Last Name" not in sheet_data.columns or "Middle Name" not in sheet_data.columns:
            continue
        
        sheet_data = sheet_data.merge(
        jurisdiction_df[['id', 'jurisdiction_name']], 
        left_on="Agency", 
        right_on="jurisdiction_name", 
        how="left"
        )

        new_df = pd.DataFrame()
        new_df['first_name'] = sheet_data[["First Name"]]
        new_df['last_name'] = sheet_data[["Last Name"]]
        new_df["middle_name"] = sheet_data["Middle Name"].fillna("")
        new_df = new_df.dropna(subset=['first_name', 'last_name'])
        new_df["cleaned_name"] = new_df["first_name"].str.lower() + " " + new_df["middle_name"].str.lower() + " " + new_df["last_name"].str.lower()
        new_df["name_suffix"] = ""
        new_df["jurisdiction_id"] = sheet_data["id"]


        if new_df is not None:
                all_officials.append(new_df)
    
    all_officials_df = pd.concat(all_officials, ignore_index=True)

    # Currently drops people with the same first and last name, needs to be fixed.
    all_officials_df = all_officials_df.drop_duplicates(subset=['cleaned_name'])

    with engine.begin() as connection:
        existing_officials = pd.read_sql(text("SELECT cleaned_name FROM officials"), con=connection)
        existing_cleaned_names = set(existing_officials['cleaned_name'])
        new_officials_df = all_officials_df[~all_officials_df['cleaned_name'].isin(existing_cleaned_names)]
        new_officials_df.to_sql("officials", con=connection, if_exists="append", index=False)


def ingest_jurisdiction_data(sheets):
    all_jurisdictions = []
    for sheet_name, sheet_data in sheets.items():
        if "Agency" not in sheet_data.columns:
            continue
        new_df = pd.DataFrame()
        new_df["jurisdiction_name"] = sheet_data["Agency"]
        new_df = new_df.dropna(subset=['jurisdiction_name'])
        new_df = new_df.drop_duplicates(subset=['jurisdiction_name'])

        if new_df is not None:
                all_jurisdictions.append(new_df)
        
    all_jurisdictions_df = pd.concat(all_jurisdictions, ignore_index=True)
    all_jurisdictions_df = all_jurisdictions_df.drop_duplicates(subset=['jurisdiction_name']) 
    
    with engine.begin() as connection:
        existing_jurisdictions = pd.read_sql(text("SELECT jurisdiction_name FROM jurisdictions"), con=connection)
        existing_jurisdiction_names = set(existing_jurisdictions['jurisdiction_name'])
        new_jurisdictions_df = all_jurisdictions_df[~all_jurisdictions_df['jurisdiction_name'].isin(existing_jurisdiction_names)]
        new_jurisdictions_df.to_sql("jurisdictions", con=connection, if_exists="append", index=False)


def clean_sheets(sheets):
    cleaned_sheets = {}

    for sheet_name, sheet_data in sheets.items():

        # modify all sheet data here, remove NaN values, etc.
        
        cleaned_sheets[sheet_name] = sheet_data
    return cleaned_sheets

# loads excel files from data/raw, returns a dictionary of sheet name to sheet data (as a pandas dataframe)
def get_sheets(file_path):

    excel_file_paths = list((file_path / "raw").glob("*.xlsx"))

    clean_sheets = {}

    for excel_file_path in excel_file_paths:

        sheets = pd.read_excel(excel_file_path, sheet_name=None)

        # Every excel file can have multiple tables
        for sheet, sheet_data in sheets.items():
            new_sheet_name = f"{excel_file_path.stem}_{sheet}"

            clean_sheets[new_sheet_name] = sheet_data

    return clean_sheets



def ingest_data(sheets):    
    ingest_jurisdiction_data(sheets)
    ingest_officials_data(sheets)


if __name__ == "__main__":
    # path to data files
    file_path = Path(__file__).resolve().parent.parent.parent / "data"

    # converts from excel to pandas dataframes
    sheets = get_sheets(file_path)

    # optionally clean the dataframes, remove NaN values, etc.
    sheets = clean_sheets(sheets)

    # ingests data into database
    ingest_data(sheets)
