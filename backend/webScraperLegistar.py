import requests
import time
import csv
import os

# --- CONFIG ---
COUNTIES = [
    "sonoma-county", "fresno", "sacramento", "eldorado", "contra-costa", "countyoflake",
    "lacounty", "monterey", "napa", "sanbernardino", "sanmateocounty", "santabarbara",
    "solano", "tehamacounty"]
CSV_FILE = "legistar_event_pipeline.csv"
SLEEP_SECONDS = 0.5

# Dates to search through
START_DATE = "2019-12-01"
END_DATE = "2019-12-31"
HEADERS = ["County", "File name", "Title", "Date", "Voters", "Link", "LastModifiedDate"]
session = requests.Session()


def safe_get(url, max_retries=5):
    backoff = 2
    for i in range(max_retries):
        try:
            resp = session.get(url)
            if resp.status_code == 429:
                print(f"Rate limit hit. Waiting {backoff}s before retry...")
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if i == max_retries - 1:
                raise e
            time.sleep(backoff)
    return None


def fetch_events_by_date(api_url, start_str, end_str):
    url = f"{api_url}/Events?$filter=EventDate ge datetime'{start_str}' and EventDate le datetime'{end_str}'"
    events = safe_get(url)
    return events if isinstance(events, list) else []


def get_matter_history_date(api_url, matter_id):
    if not matter_id:
        return None
    url = f"{api_url}/Matters/{matter_id}/Histories"
    try:
        history_records = safe_get(url)
    except Exception as e:
        print(f" Warning: Could not fetch history for Matter ID {matter_id}: {e}")
        return None
    if history_records and isinstance(history_records, list):
        for record in history_records:
            action_date = record.get("MatterHistoryActionDate")
            if action_date:
                return action_date
    return None


def load_existing_natural_keys(file_name):
    existing_keys = set()
    if os.path.exists(file_name):
        with open(file_name, "r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            header = next(reader, None)

            try:
                county_idx = header.index("County") if header else 0
                file_idx = header.index("File name") if header else 1
            except (ValueError, AttributeError):
                county_idx, file_idx = 0, 1

            for row in reader:
                if row and len(row) > max(county_idx, file_idx):
                    # Create a compound lookup key out of raw row data values
                    key_string = f"{row[county_idx]}_{row[file_idx]}"
                    existing_keys.add(key_string)
    return existing_keys


def process_county_events(county, writer, site_link, existing_keys):
    api_url = f"https://webapi.legistar.com/v1/{county}"

    # Get all events matching the specific date filter
    events = fetch_events_by_date(api_url, START_DATE, END_DATE)
    print(f" Found {len(events)} events for {county} between {START_DATE} and {END_DATE}")

    for event in events:
        event_id = event.get("EventId")
        if not event_id:
            continue

        # Get all EventItems for this specific eventId
        items_url = f"{api_url}/Events/{event_id}/EventItems"
        event_items = safe_get(items_url)
        if not event_items or not isinstance(event_items, list):
            continue

        for item in event_items:
            # Exclude empty ItemActionIds
            if not item.get("EventItemActionId"):
                continue

            # Extract target elements
            matter_id = item.get("EventItemMatterId")
            event_item_id = item.get("EventItemId")
            matter_file = item.get("EventItemMatterFile")  # File name
            last_modified = item.get("EventItemLastModifiedUtc")

            # Skip items not linked to a file matter tracking string
            if not matter_id or not matter_file:
                continue

            natural_composite_key = f"{county}_{matter_file}"
            if natural_composite_key in existing_keys:
                print(f"Skipping: {county}_{matter_file}")
                continue

            action_date = item.get("EventItemActionDate")
            if not action_date and matter_id:
                action_date = get_matter_history_date(api_url, matter_id)
                time.sleep(SLEEP_SECONDS)

            if action_date and "T" in str(action_date):
                action_date = str(action_date).split("T")[0]
            else:
                action_date = str(action_date) if action_date else "Unknown Date"

            # Target the votes endpoint for this specific EventItemId
            votes_url = f"{api_url}/EventItems/{event_item_id}/Votes"
            votes_data = safe_get(votes_url)
            time.sleep(SLEEP_SECONDS)  # Throttle

            vote_names = []
            if votes_data and isinstance(votes_data, list):
                vote_names = [v.get("VotePersonName") for v in votes_data if v.get("VotePersonName")]

            # Fallback for grouped approvals/consent text on itemized records
            if not vote_names:
                vote_value = item.get("EventItemVoteValueName", "")
                action_name = item.get("EventItemActionName", "")
                if any(k in str(vote_value).lower() or k in str(action_name).lower() for k in
                       ["consent", "unanimous", "approved", "passed"]):
                    vote_names = ["Board Unanimous / Consent Calendar"]

            if last_modified and "T" in str(last_modified):
                last_modified = str(last_modified).split("T")[0]
            else:
                last_modified = str(last_modified) if last_modified else "Unknown"

            title = item.get("EventItemTitle")
            current_link = f"{site_link}{matter_id}"
            if vote_names == [""]:
                vote_names = ["No voting data found"]

            writer.writerow([
                county,
                matter_file,
                title,
                action_date,
                ", ".join(vote_names),
                current_link,
                last_modified
            ])

            # Dynamically update cache to catch duplicates in the active loop run
            existing_keys.add(natural_composite_key)


def run_pipeline():
    # Ingest all historical keys prior to starting the network loop
    existing_keys = load_existing_natural_keys(CSV_FILE)
    if existing_keys:
        print(f" Loaded {len(existing_keys)} unique file-action dates from disk. Resuming...")

    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

    for county in COUNTIES:
        print(f"\nProcessing Pipeline for County: {county}...")
        site_link = f"https://{county}.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key="

        with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            process_county_events(county, writer, site_link, existing_keys)
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    run_pipeline()
    print("\nTargeted execution loop complete.")
