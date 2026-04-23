import requests
import time
import csv
from datetime import datetime, timedelta

BASE_URL = "https://webapi.legistar.com/v1/sonoma-county"
# base link for matters https://sonoma-county.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key={MatterId}

# --- CONFIG ---
YEARS_BACK = 5
CSV_FILE = "legistar_data1.csv"
SLEEP_SECONDS = 0.5

def safe_get(url, max_retries=5):
    # Rate limiter
    backoff = 2
    for i in range(max_retries):
        try:
            resp = requests.get(url)

            if resp.status_code == 429:
                print(f"Rate limit hit. Waiting {backoff}s before retry...")
                time.sleep(backoff)
                backoff *= 2
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            if i == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {url}")
                raise e
            time.sleep(backoff)
    return None

def fetch_matters(cutoff):
    all_matters = []
    page_size = 100
    skip = 0

    while True:
        url = (
            f"{BASE_URL}/Matters"
            f"?$filter=MatterPassedDate ge datetime'{cutoff.year}-{cutoff.month:02d}-{cutoff.day:02d}'"
            f"&$top={page_size}&$skip={skip}"
        )

        matters = safe_get(url)
        if not matters:
            break

        all_matters.extend(matters)
        print(f"Fetched {len(all_matters)} total matters...")

        skip += page_size
        time.sleep(SLEEP_SECONDS)

    return all_matters

def get_matter_history(matter_id):
    url = f"{BASE_URL}/Matters/{matter_id}/Histories"
    return safe_get(url)

def get_matter_text(matter_id):
    # 1. Get versions
    url = f"{BASE_URL}/Matters/{matter_id}/Versions"
    versions = safe_get(url)

    if not versions or not isinstance(versions, list):
        return {}

    # 2. Get the key from the first entry
    key = versions[0].get("Key")
    if not key:
        return {}

    # 3. Get text using the key
    url = f"{BASE_URL}/Matters/{matter_id}/Texts/{key}"
    return safe_get(url)


def get_names(matter_text):
    if not matter_text:
        return []

    anchor = "Staff Name and Phone Number:"
    if anchor in matter_text:
        after_anchor = matter_text.split(anchor)[1]
        names_block = after_anchor.split('\n')[0].strip()
        entries = names_block.split(',')

        found_names = []
        for entry in entries:
            entry = entry.strip()
            name_only = ""
            for char in entry:
                if char.isdigit(): break
                name_only += char

            name = name_only.strip()
            if name.lower().startswith("and "):
                name = name[4:].strip()
            if name:
                found_names.append(name)
        return found_names
    return []

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

        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    csv_writer(CSV_FILE)
