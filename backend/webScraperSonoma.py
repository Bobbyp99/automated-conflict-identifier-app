import requests
import re
import time
import csv
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
COUNTY_NAME    = "sonoma-county"
API_URL        = f"https://webapi.legistar.com/v1/{COUNTY_NAME}"
SITE_LINK      = f"https://sonoma-county.legistar.com/gateway.aspx?m=l&id=/matter.aspx?key="
CSV_FILE       = "decisions_test2.csv"
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


def fetch_matter_text(matter_id, matter_guid):
    """
    Scrapes the legislation detail web page for the matter body text.
    The /Matters/{id}/Texts API endpoint returns 405 for Sonoma County.
    Staff names live in the Text tab of the detail page.
    """
    if not matter_guid:
        return ""
    url = (
        f"https://sonoma-county.legistar.com/LegislationDetail.aspx"
        f"?ID={matter_id}&GUID={matter_guid}&Options=ID%7CText%7C&Search="
    )
    try:
        resp = requests.get(url, timeout=30)
        if not resp.ok:
            return ""
        html = resp.text
        m = re.search(r'Staff Names? and Phone Numbers?', html, re.IGNORECASE)
        if not m:
            return ""
        # Grab a window of HTML from that point, strip tags, collapse whitespace
        chunk = html[m.start(): m.start() + 600]
        plain = re.sub(r'<[^>]+>', ' ', chunk)
        plain = re.sub(r'&[a-z]+;', ' ', plain)   # strip HTML entities
        plain = re.sub(r'\s+', ' ', plain).strip()
        return plain
    except requests.exceptions.RequestException:
        return ""


def extract_staff_names(text):
    """
    Parse 'Staff Name and Phone Number: Alice, Bob, (707) 555-1234'
    from matter text and return a list of name strings only.
    """
    if not text:
        return []
    match = re.search(
        r'Staff Names? and Phone Numbers?:\s*(.+?)(?:\r?\n|$)',
        text, re.IGNORECASE
    )
    if not match:
        return []
    raw = match.group(1).strip()
    parts = [p.strip() for p in raw.split(',')]
    names = []
    for part in parts:
        # Drop phone numbers like (707) 565-2431 or 707-565-2431
        if re.search(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}', part):
            continue
        # Drop anything starting with a digit (extension numbers, etc.)
        if re.match(r'^\d', part):
            continue
        if part:
            names.append(part)
    return names


def get_final_action(matter_id):
    """
    Returns the most relevant history entry as a dict, or None.
    Prefers entries with a PassedFlag (actual votes) over procedural ones.
    """
    history = safe_get(f"{API_URL}/Matters/{matter_id}/Histories") or []
    if not history:
        return None

    # Prefer entries that have a vote result
    voted = [h for h in history if h.get("MatterHistoryPassedFlag") is not None]
    entries = voted if voted else history
    # Take the most recent entry by date
    entries.sort(key=lambda h: h.get("MatterHistoryActionDate") or "", reverse=True)
    return entries[0]


def get_voters(history_entry, matter_id):
    """
    Given a history entry, fetch voter names for the corresponding event item.
    Matches on EventItemMatterId (not GUID — MatterHistoryGuid != EventItemGuid).
    """
    if not history_entry:
        return []
    event_id = history_entry.get("MatterHistoryEventId")
    if not event_id:
        return []

    items = safe_get(f"{API_URL}/Events/{event_id}/EventItems") or []
    for item in items:
        # str() on both sides avoids silent int/str type mismatches
        if str(item.get("EventItemMatterId")) == str(matter_id):
            event_item_id = item.get("EventItemId")
            votes = safe_get(f"{API_URL}/EventItems/{event_item_id}/Votes") or []
            return [v.get("VotePersonName", "") for v in votes if v.get("VotePersonName")]
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
            "File Number",
            "Title",
            "Type",
            "Status",
            "File Created",
            "Final Action Date",
            "Final Action",
            "Result",
            "Staff Names",
            "Mover",
            "Seconder",
            "Voters",
            "Link",
        ])
        f.flush()

        total = len(matters)
        for i, matter in enumerate(matters, 1):
            matter_id   = matter.get("MatterId")
            matter_guid = matter.get("MatterGuid", "")
            file_num    = matter.get("MatterFile", "")
            title       = matter.get("MatterTitle", "")
            m_type      = matter.get("MatterTypeName", "")
            status      = matter.get("MatterStatusName", "")
            intro       = (matter.get("MatterIntroDate") or "")[:10]
            link        = f"{SITE_LINK}{matter_id}"

            print(f"\n[{i}/{total}] {file_num} — {title[:70]}")

            final = get_final_action(matter_id)
            if final:
                action_date = (final.get("MatterHistoryActionDate") or "")[:10]
                action      = final.get("MatterHistoryActionName", "")
                result      = final.get("MatterHistoryPassedFlagName", "")
                mover       = final.get("MatterHistoryMoverName", "")
                seconder    = final.get("MatterHistorySeconderName", "")
                voters      = get_voters(final, matter_id)
            else:
                action_date = action = result = mover = seconder = ""
                voters = []

            text        = fetch_matter_text(matter_id, matter_guid)
            staff_names = extract_staff_names(text)

            print(f"  Action: {action} | Result: {result} | Voters: {len(voters)} | Staff: {staff_names}")

            writer.writerow([
                file_num,
                title,
                m_type,
                status,
                intro,
                action_date,
                action,
                result,
                ", ".join(staff_names),
                mover,
                seconder,
                ", ".join(voters),
                link,
            ])
            f.flush()
            rows_written += 1

            time.sleep(SLEEP_SECONDS)

    print(f"\nDone. {rows_written} rows written to {CSV_FILE}")


if __name__ == "__main__":
    scrape()
