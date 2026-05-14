import requests
import csv
import time
import re
from bs4 import BeautifulSoup
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
DECISIONS_CSV  = "decisions_test6.csv"
INTERESTS_CSV  = "income_sources2.csv"
OUTPUT_CSV     = "flagged_conflicts2.csv"
SLEEP_SEC      = 1.5
MIN_ENTITY_LEN = 5    # ignore blank or trivially short entity names
YEAR_WINDOW    = 1    # match interests within ±1 filing year of vote year

# These values appear in the entity column but are too generic to search for
SKIP_ENTITIES = {"", "other", "salary", "stock", "ownership/deed of trust"}

# Matters with these title patterns are ceremonial — no financial transaction possible
CEREMONIAL_PATTERNS = re.compile(
    r"adopt a (gold |silver )?resolution|proclamation|honoring|commending|"
    r"recognizing|in memory of|in honor of",
    re.IGNORECASE,
)


# ── Data loading ──────────────────────────────────────────────────────────────

def load_interests():
    """
    Returns dict: official_name -> list of interest dicts.
    Skips Schedule D (gifts), blank/generic entity names, and entries where
    the entity name matches the official's own name (self-salary entries).
    """
    interests = defaultdict(list)
    with open(INTERESTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Drop gifts entirely
            if row["Schedule"].startswith("D"):
                continue
            official = row["Official Name"].strip()
            entity   = row["Name of Business Entity or Source"].strip()

            # Drop blank/generic and self-referential entries
            if len(entity) < MIN_ENTITY_LEN:
                continue
            if entity.lower() in SKIP_ENTITIES:
                continue
            if entity.lower() == official.lower():
                continue

            # Drop if entity is just the official's first or last name
            name_parts = {p.lower() for p in official.split()}
            if entity.lower() in name_parts:
                continue

            # Drop dissolved companies — no active financial interest
            if "dissolved" in entity.lower():
                continue

            # Drop single-word entities shorter than 8 chars — too generic to match reliably
            if " " not in entity and len(entity) < 8:
                continue

            # Drop spouse/family names that share the official's last name
            # e.g. "Elizabeth Gore (Spouse)" → "Elizabeth Gore" shares last name "Gore"
            official_last = official.split()[-1].lower()
            core = re.split(r'\s*\(', entity)[0].strip()  # strip parenthetical like "(Spouse)"
            core_words = core.split()
            if len(core_words) >= 2 and core_words[-1].lower() == official_last:
                continue

            interests[official].append({
                "entity":   entity,
                "year":     row["Filing Year"],
                "schedule": row["Schedule"],
            })
    return interests


def load_decisions():
    """
    Returns dict: url -> list of vote rows for that matter.
    Each matter has one URL but up to 5 vote rows (one per supervisor).
    """
    by_url = defaultdict(list)
    with open(DECISIONS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_url[row["Link"]].append(row)
    return by_url


# ── Page fetching ─────────────────────────────────────────────────────────────

def fetch_page_text(url):
    """Fetch a Legistar matter page and return its visible text content."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"  Error fetching page: {e}")
        return ""


# ── Matching ──────────────────────────────────────────────────────────────────

def entity_matches(entity, text):
    """
    Case-insensitive search for entity name in page text.
    For names with parentheticals like "HPE (Hewlett Packard Enterprises Company)",
    searches the abbreviation and the full name separately so either form matches.
    """
    candidates = [entity]
    paren = re.match(r'^(.+?)\s*\((.+)\)$', entity)
    if paren:
        candidates.append(paren.group(1).strip())
        candidates.append(paren.group(2).strip())

    for part in candidates:
        if len(part) >= MIN_ENTITY_LEN:
            if re.search(re.escape(part), text, re.IGNORECASE):
                return True
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def scan():
    print("Loading interests and decisions...")
    interests = load_interests()
    by_url    = load_decisions()

    unique_urls = list(by_url.keys())
    total       = len(unique_urls)
    print(f"Scanning {total} unique matters — estimated {total * SLEEP_SEC / 60:.0f} min\n")

    flagged_count = 0

    fields = [
        "Official Name", "Vote Outcome", "File Number",
        "Agenda Item Subject", "Vote Date", "Meeting Type",
        "Overall Result", "Entity Matched", "Interest Schedule",
        "Interest Year", "Link",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        out.flush()

        for i, url in enumerate(unique_urls, 1):
            vote_rows = by_url[url]
            sample    = vote_rows[0]
            print(f"[{i}/{total}] {sample['File Number']} — {sample['Agenda Item Subject'][:65]}")

            # Skip ceremonial matters — no financial transaction possible
            if CEREMONIAL_PATTERNS.search(sample["Agenda Item Subject"]):
                continue

            text = fetch_page_text(url)
            if not text:
                time.sleep(SLEEP_SEC)
                continue

            try:
                vote_year = int(sample["Vote Date"][:4])
            except (ValueError, TypeError):
                vote_year = None

            for vote_row in vote_rows:
                official = vote_row["Official Name"]
                outcome  = vote_row["Vote Outcome"]

                if outcome == "Absent":
                    continue

                for interest in interests.get(official, []):
                    # Only match interests from years close to the vote
                    try:
                        if vote_year and abs(int(interest["year"]) - vote_year) > YEAR_WINDOW:
                            continue
                    except (ValueError, TypeError):
                        pass

                    if entity_matches(interest["entity"], text):
                        writer.writerow({
                            "Official Name":       official,
                            "Vote Outcome":        outcome,
                            "File Number":         vote_row["File Number"],
                            "Agenda Item Subject": vote_row["Agenda Item Subject"],
                            "Vote Date":           vote_row["Vote Date"],
                            "Meeting Type":        vote_row["Meeting Type"],
                            "Overall Result":      vote_row["Overall Result"],
                            "Entity Matched":      interest["entity"],
                            "Interest Schedule":   interest["schedule"],
                            "Interest Year":       interest["year"],
                            "Link":                url,
                        })
                        out.flush()
                        flagged_count += 1
                        print(f"  *** FLAGGED: {official} — {interest['entity']}")

            time.sleep(SLEEP_SEC)

    print(f"\nDone. {flagged_count} potential conflicts written to {OUTPUT_CSV}")


if __name__ == "__main__":
    scan()
