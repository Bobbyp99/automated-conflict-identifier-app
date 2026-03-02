import sys

# install pandas
# install openpyxl for reading excel files
import pandas as pd


from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).parents[1]))
from database import engine

# gets information about each official
def get_official_data(sheet_data):
    if "First Name" not in sheet_data.columns or "Last Name" not in sheet_data.columns or "Middle Name" not in sheet_data.columns:
        return
    new_df = pd.DataFrame()
    new_df['first_name'] = sheet_data[["First Name"]]
    new_df['last_name'] = sheet_data[["Last Name"]]
    new_df["middle_name"] = sheet_data["Middle Name"].fillna("")
    new_df = new_df.dropna(subset=['first_name', 'last_name'])
    new_df["cleaned_name"] = new_df["first_name"].str.lower() + " " + new_df["middle_name"].str.lower() + " " + new_df["last_name"].str.lower()
    new_df["name_suffix"] = ""
    new_df["jurisdiction_id"] = 1

    return new_df

def get_jurisdiction_data(sheet_data):
    if "Agency" not in sheet_data.columns:
        return
    new_df = pd.DataFrame()
    new_df["jurisdiction_name"] = sheet_data[["Agency"]]
    new_df = new_df.dropna(subset=['jurisdiction_name'])
    new_df = new_df.drop_duplicates(subset=['jurisdiction_name'])

    return new_df



def ingest_data(sheets):
    all_jurisdictions = []
    all_officials = []
    # NEED TO ADD A WAY TO ADD JURISDICTIONS FIRST, SO THAT WE CAN USE THAT ID TO LINK OFFICIALS TO JURISDICTIONS, CURRENTLY JUST SETTING ALL JURISDICTION IDS TO 1 FOR TESTING PURPOSES
    for sheet_name, sheet_data in sheets.items():
        jurisdictions_df = get_jurisdiction_data(sheet_data)
        # officials_df = get_official_data(sheet_data)

        if jurisdictions_df is not None:
                all_jurisdictions.append(jurisdictions_df)
        # if officials_df is not None:
        #     all_officials.append(officials_df)
    
    all_jurisdictions_df = pd.concat(all_jurisdictions, ignore_index=True)
    all_jurisdictions_df = all_jurisdictions_df.drop_duplicates(subset=['jurisdiction_name'])

    # all_officials_df = pd.concat(all_officials, ignore_index=True)
    # all_officials_df = all_officials_df.drop_duplicates(subset=['cleaned_name'])

    save_to_postgres(all_jurisdictions_df, "jurisdictions")
    # save_to_postgres(all_officials_df, "officials")
        

def clean_sheets(sheets):
    cleaned_sheets = {}

    for sheet_name, sheet_data in sheets.items():

        # modify all sheet data here, remove NaN values, etc.
        


        cleaned_sheets[sheet_name] = sheet_data
    return cleaned_sheets


# currently reads excel files, and save each sheet as a csv file in the processed data directory
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


def save_to_postgres(df, table_name):
    with engine.connect() as connection:
        df.to_sql(table_name, con=connection, if_exists='append', index=False)





if __name__ == "__main__":
    # path to data files
    file_path = Path(__file__).resolve().parent.parent.parent / "data"

    sheets = get_sheets(file_path)
    sheets = clean_sheets(sheets)
    ingest_data(sheets)


# current problems
# Currently takes in duplicates of officials and jurisdictions when taking in new data.
