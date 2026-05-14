import requests
import time
import csv
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
COUNTY_NAME    = "sonoma-county"
API_URL        = f"https://webapi.legistar.com/v1/{COUNTY_NAME}"
SITE_LINK      = f"https://sonoma-county.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key="
CSV_FILE       = "decisions_test5.csv"
YEARS_BACK     = 5
SLEEP_SECONDS  = 0.5


# ── HTTP ──────────────────────────────────────────────────────────────────────

def safe_get(url, max_retries=5):
    backoff = 2
    for i in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 429:
                print(f"  Rate limited. Waiting {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            if not resp.ok:
                print(f"  HTTP {resp.status_code} on attempt {i+1}: {url}")
                print(f"  Response: {resp.text[:300]}")
                if i == max_retries - 1:
                    return None
                time.sleep(backoff)
                backoff *= 2
                continue
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"  Network error on attempt {i+1}: {e}")
            if i == max_retries - 1:
                return None
            time.sleep(backoff)
            backoff *= 2
    return None


# ── Legistar API calls ────────────────────────────────────────────────────────

def fetch_matters(cutoff):
    all_matters = []
    page_size   = 100
    skip        = 0
    date_str    = f"{cutoff.year}-{cutoff.month:02d}-{cutoff.day:02d}"

    print(f"Fetching matters introduced since {date_str}...")

    while True:
        url = (
            f"{API_URL}/Matters"
            f"?$filter=MatterIntroDate ge datetime'{date_str}'"
            f"&$top={page_size}&$skip={skip}"
        )
        batch = safe_get(url)
        if not batch:
            break
        all_matters.extend(batch)
        print(f"  Fetched {len(all_matters)} matters so far...")
        if len(batch) < page_size:
            break
        skip += page_size
        time.sleep(SLEEP_SECONDS)

    print(f"  Total matters: {len(all_matters)}")
    return all_matters


def get_final_action(matter_id):
    """Returns the most relevant history entry, preferring entries with a recorded vote."""
    history = safe_get(f"{API_URL}/Matters/{matter_id}/Histories") or []
    if not history:
        return None

    voted = [h for h in history if h.get("MatterHistoryPassedFlag") is not None]
    entries = voted if voted else history
    entries.sort(key=lambda h: h.get("MatterHistoryActionDate") or "", reverse=True)
    return entries[0]


def get_event_body(event_id):
    """Returns the meeting body name (e.g. 'Board of Supervisors')."""
    if not event_id:
        return ""
    event = safe_get(f"{API_URL}/Events/{event_id}")
    if not event:
        return ""
    return event.get("EventBodyName", "")


def get_individual_votes(history_entry, matter_id):
    """
    Returns a list of {name, outcome} dicts — one per supervisor who voted.
    VoteValueName gives the per-person outcome: Yes, No, Abstain, etc.
    """
    if not history_entry:
        return []
    event_id = history_entry.get("MatterHistoryEventId")
    if not event_id:
        return []

    items = safe_get(f"{API_URL}/Events/{event_id}/EventItems") or []
    for item in items:
        if str(item.get("EventItemMatterId")) == str(matter_id):
            event_item_id = item.get("EventItemId")
            votes = safe_get(f"{API_URL}/EventItems/{event_item_id}/Votes") or []
            return [
                {
                    "name":    v.get("VotePersonName", ""),
                    "outcome": v.get("VoteValueName", ""),
                }
                for v in votes if v.get("VotePersonName")
            ]
    return []


# ── Main ──────────────────────────────────────────────────────────────────────

def scrape():
    cutoff  = datetime.now() - timedelta(days=365 * YEARS_BACK)
    matters = fetch_matters(cutoff)

    if not matters:
        print("No matters found. Check API connection or COUNTY_NAME.")
        return

    rows_written = 0

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Official Name",
            "Vote Outcome",
            "File Number",
            "Agenda Item Subject",
            "Vote Date",
            "Meeting Type",
            "Overall Result",
            "Link",
        ])
        f.flush()

        total = len(matters)
        for i, matter in enumerate(matters, 1):
            matter_id = matter.get("MatterId")
            file_num  = matter.get("MatterFile", "")
            title     = matter.get("MatterTitle", "")
            link      = f"{SITE_LINK}{matter_id}"

            print(f"\n[{i}/{total}] {file_num} — {title[:70]}")

            final = get_final_action(matter_id)
            if final:
                action_date  = (final.get("MatterHistoryActionDate") or "")[:10]
                result       = final.get("MatterHistoryPassedFlagName", "")
                event_id     = final.get("MatterHistoryEventId")
                meeting_type = get_event_body(event_id)
                votes        = get_individual_votes(final, matter_id)
            else:
                action_date = result = meeting_type = ""
                votes = []

            print(f"  Result: {result} | Meeting: {meeting_type} | Votes: {len(votes)}")

            for vote in votes:
                writer.writerow([
                    vote["name"],
                    vote["outcome"],
                    file_num,
                    title,
                    action_date,
                    meeting_type,
                    result,
                    link,
                ])
                f.flush()
                rows_written += 1

            time.sleep(SLEEP_SECONDS)

    print(f"\nDone. {rows_written} rows written to {CSV_FILE}")


if __name__ == "__main__":
    scrape()
