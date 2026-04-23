import requests
import time
import csv
from datetime import datetime, timedelta

BASE_URL = "https://webapi.legistar.com/v1/sonoma-county"

# --- CONFIG ---
YEARS_BACK = 5
SLEEP_SECONDS = 0.2
CSV_FILE = "legistar_data.csv"

def fetch_matters(cutoff):
    while True:
        url = (
            f"{BASE_URL}/Matters"
            f"?$filter=MatterPassedDate%20ge%20"
            f"datetime%27{cutoff.year}-{cutoff.month:02d}-{cutoff.day}%27"
        )

        resp = requests.get(url)
        resp.raise_for_status()
        matters = resp.json()
        return matters

def get_matter_history(matter_id):
    url = f"{BASE_URL}/Matters/{matter_id}/Histories"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def get_matter_text(matter_id):
    url = f"{BASE_URL}/Matters/{matter_id}/Versions"
    resp = requests.get(url)
    resp.raise_for_status()
    site_text = resp.json()

    for t in site_text:
        key = t.get("Key")

    url = f"{BASE_URL}/Matters/{matter_id}/Texts/{key}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def get_names(matter_text):
    anchor = "Staff Name and Phone Number:"
    try:
        if anchor in matter_text:
            after_anchor = matter_text.split(anchor)[1]
            names_block = after_anchor.split('\n')[0].strip()
            entries = names_block.split(',')

            found_names = []
            for entry in entries:
                entry = entry.strip()
                name_only = ""

                for char in entry:
                    if char.isdigit():
                        break
                    name_only += char

                names_only = name_only.strip()
                if names_only.lower().startswith("and "):
                    names_only = names_only[4:].strip()

                found_names.append(names_only)

            return found_names
    except TypeError as e:
        return ""


def csv_writer(file_name):
    with open(file_name, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["File name",
                         "Title",
                         "Action",
                         "Status",
                         "Date",
                         "Movers",
                         "Staff Names",
                         "Link"])
        extract_data(writer)

def extract_data(csv, years_back=YEARS_BACK):
    cutoff = datetime.now() - timedelta(days=365 * years_back)

    for matter in fetch_matters(cutoff):
        matter_id = matter.get("MatterId")
        title = matter.get("MatterTitle")
        matter_file = matter.get("MatterFile")
        matter_status = matter.get("MatterStatusName")
        matter_text = get_matter_text(matter_id)
        staff_names = get_names(matter_text.get("MatterTextPlain"))
        try:
            history = get_matter_history(matter_id)
        except Exception as e:
            print(f"Error fetching history for {matter_id}: {e}")
            continue

        for h in history:
            action = h.get("MatterHistoryActionName")
            action_date = h.get("MatterHistoryActionDate")
            mover_name = h.get("MatterHistoryMoverName")
            seconder_name = h.get("MatterHistorySecondName")

            print("\n==============================")
            print("File: ", matter_file)
            print("Title:", title)
            print("Action:", action)
            print("Status:", matter_status)
            print("Date:", action_date)
            print(f"Mover: {mover_name}, Seconder: {seconder_name}", )
            print("Staff Names: ", end="")
            if staff_names:
                for name in staff_names:
                    print(f"{name}, ", end="")
            else:
                print("None")

            print(f"\nLink: https://sonoma-county.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key={matter_id}")

            csv.writerow([matter_file,
                          title,
                          action,
                          matter_status,
                          action_date,
                          f"{mover_name}, {seconder_name}",
                          staff_names,
                          f"https://sonoma-county.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key={matter_id}"])

        # Dont kill API
        time.sleep(SLEEP_SECONDS)

# base link for rebuild https://sonoma-county.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key={MatterId}

if __name__ == "__main__":
    csv_writer(CSV_FILE)
