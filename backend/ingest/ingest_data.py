import pandas as pd
from pathlib import Path
from backend.database import engine, SessionLocal
from backend.models import Jurisdictions, Officials

def read_from_file(filepath: str, keyword: str) -> list[pd.Series]: # Reads from specified file a specified keyword.
    series_list = [] # Returns a list of series, basically just columns of relevant data.
    fixed_sheets = pd.read_excel(filepath, sheet_name=None) # Returns dictionary with (sheet_name, dataframe).
    # It is the name of the sheet and the dataframe that corresponds to it.

    for sheet_name, df in fixed_sheets.items():
        if keyword in df.columns:
            series_list.append(df[keyword])
        else:
            mask = (df == keyword) # Create a dataframe where each cell contains boolean values, a row contains true if it contains the keyword.
            keyword_column = df.columns[mask.any()] # Get the column of the row that contains the keyword.
            column_name = keyword_column[0] # Identify what the column name is actually called, likely "Unamed: NUMBER"
  
            start_index = df[df[column_name] == keyword].index[0] # Gets row index 
            start_pos = df.index.get_loc(start_index) # Gets the offset of start_index

            values_below = df[column_name].iloc[start_pos + 1:] # Get the specified series, in this case the values below the keyword

            series_list.append(values_below)

    return series_list

def add_jurisdictions(filepath: str): # Add to DB
    all_jurisdictions = read_from_file(filepath, "Agency")
    
    database_jurisdictions = pd.read_sql("SELECT * FROM jurisdictions", engine)["jurisdiction_name"]

    all_jurisdictions = pd.concat(all_jurisdictions, ignore_index=True)
    all_jurisdictions = all_jurisdictions.astype(str).dropna().drop_duplicates()

    all_jurisdictions = all_jurisdictions[~all_jurisdictions.isin(database_jurisdictions)]

    with SessionLocal() as session:
        
        for value in all_jurisdictions:
            session.add(Jurisdictions(jurisdiction_name = value))
        
        session.commit()

def add_officials(filepath: str): # Add to DB
    all_first_names = read_from_file(filepath, "First Name")
    all_middle_names = read_from_file(filepath, "Middle Name")
    all_last_names = read_from_file(filepath, "Last Name")
    all_agencies = read_from_file(filepath, "Agency")

    for i in range(len(all_first_names)):
        all_first_names[i] = all_first_names[i].astype(str).fillna("")

    for i in range(len(all_middle_names)):
        all_middle_names[i] = all_middle_names[i].astype(str).fillna("")

    for i in range(len(all_last_names)):
        all_last_names[i] = all_last_names[i].astype(str).fillna("")

    all_first_names = pd.concat(all_first_names, ignore_index=True)
    all_middle_names = pd.concat(all_middle_names, ignore_index=True)
    all_last_names = pd.concat(all_last_names, ignore_index=True)
    all_agencies = pd.concat(all_agencies, ignore_index=True)

    combined_df = pd.DataFrame({"first_name": all_first_names, "middle_name": all_middle_names, "last_name": all_last_names, "Agency": all_agencies})

    database_jurisdictions_df = pd.read_sql("SELECT * FROM jurisdictions", engine)

    merge_df = pd.merge(database_jurisdictions_df, combined_df, left_on="jurisdiction_name", right_on="Agency", how="inner")
    merge_df = merge_df.drop_duplicates().dropna()
    merge_df["cleaned_name"] = merge_df["first_name"].str.lower() + merge_df["middle_name"].str.lower() + merge_df["last_name"].str.lower()

    database_officials_df = pd.read_sql("SELECT * FROM officials", engine)

    merge_df = merge_df[~merge_df['cleaned_name'].isin(database_officials_df["cleaned_name"])]

    with SessionLocal() as session:
        
        for index, value in merge_df.iterrows():
            session.add(Officials(  first_name = value["first_name"],
                                    middle_name = value["middle_name"],
                                    last_name = value["last_name"],
                                    cleaned_name = value["cleaned_name"],
                                    name_suffix = "",
                                    jurisdiction_id = value["id"]))
        
        session.commit()

if __name__ == "__main__":
    # path to data files
    file_path = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

    for path in file_path.glob("*.xlsx"):
        add_jurisdictions(str(path))
        add_officials(str(path))