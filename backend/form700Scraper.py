import requests
import json
import csv
import time

# ── Config ────────────────────────────────────────────────────────────────────
FPPC_URL  = "https://form700search.fppc.ca.gov/Home/SearchDocuments"
CSV_FILE  = "income_sources2.csv"
AGENCY    = "Sonoma County"
SLEEP_SEC = 1.0

# Names taken from vote records in decisions.csv — update if board membership changes
SUPERVISORS = [
    ("Susan",  "Gorin"),
    ("David",  "Rabbitt"),
    ("Chris",  "Coursey"),
    ("James",  "Gore"),
    ("Lynda",  "Hopkins"),
]


# ── FPPC API ──────────────────────────────────────────────────────────────────

def fetch_filings(first_name, last_name):
    """
    Fetch all Form 700 filings for a given official from the FPPC search API.
    Passing empty-string interest returns all schedules (no filter on content).
    """
    payload = {
        "queryGenerationInfo": None,
        "searchFieldQueryInfos": [
            {"queryField": "FilerAgency",              "filterValue": AGENCY},
            {"queryField": "FilerFirstName",           "queryType": "Start With", "filterValue": first_name},
            {"queryField": "FilerLastName",            "queryType": "Start With", "filterValue": last_name},
            {"queryField": "FilingType",               "filterValue": []},
            {"queryField": "ScheduleA1MultiFields",    "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleA1Comments",       "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleA2MultiFields",    "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleA2Comments",       "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleBMultiFields",     "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleBComments",        "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleCIncomeMultiFields","filterValue": "","queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleCLoanMultiFields", "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleCComments",        "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleDMultiFields",     "filterValue": "", "queryType": "MultiFields Exact Phrase"},
            {"queryField": "ScheduleEMultiFields",     "filterValue": "", "queryType": "MultiFields Exact Phrase"},
        ],
        "showOnlyHeldPositions": False,
    }

    try:
        resp = requests.post(FPPC_URL, json=payload, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
        # The API returns a JSON-encoded string inside the JSON envelope
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data
    except Exception as e:
        print(f"  Error fetching {first_name} {last_name}: {e}")
        return None


def extract_rows(data, first_name, last_name):
    """
    Parse the FPPC API response into flat rows suitable for the CSV.
    Each row represents one financial interest (one schedule entry).
    """
    if not data:
        return []

    docs = data.get("documents", [])
    if not isinstance(docs, list):
        print(f"  Unexpected response shape for {first_name} {last_name} — check raw_response.json")
        return []

    rows = []
    official = f"{first_name} {last_name}"

    def fmt_value(v):
        """Format a {gte, lte} range dict into a readable dollar range."""
        if isinstance(v, dict):
            gte, lte = v.get("gte", ""), v.get("lte", "")
            return f"${gte:,} - ${lte:,}" if gte != "" and lte != "" else str(v)
        return str(v) if v is not None else ""

    for doc in docs:
        schedules = doc.get("filingData", {}).get("schedules", {})
        positions = doc.get("filingPositions", [])

        # Prefer the County of Sonoma Supervisor position for filing metadata
        pos = next(
            (p for p in positions if p.get("position") == "Supervisor"),
            positions[0] if positions else {}
        )
        year        = pos.get("filingYear", "")
        filing_type = pos.get("filingType", "")

        # ── Schedule A-1: Publicly traded investments ─────────────────────────
        for entry in (schedules.get("scheduleA1") or {}).get("sections") or []:
            rows.append([
                official, year, filing_type,
                "A1 - Publicly Traded Investment",
                entry.get("nameOfBusinessEntity", ""),
                fmt_value(entry.get("fairMarketValue")),
                entry.get("natureOfInvestment", ""),
            ])

        # ── Schedule A-2: Private business investments ────────────────────────
        for entry in (schedules.get("scheduleA2") or {}).get("sections") or []:
            rows.append([
                official, year, filing_type,
                "A2 - Private Business Investment",
                entry.get("nameOfBusinessEntity", ""),
                fmt_value(entry.get("fairMarketValue")),
                entry.get("businessActivity", ""),
            ])

        # ── Schedule B: Real property ─────────────────────────────────────────
        for entry in (schedules.get("scheduleB") or {}).get("sections") or []:
            rows.append([
                official, year, filing_type,
                "B - Real Property",
                entry.get("parcelOrAddress") or entry.get("location", ""),
                fmt_value(entry.get("fairMarketValue")),
                entry.get("natureOfInterest", ""),
            ])

        # ── Schedule C: Income sources ────────────────────────────────────────
        for entry in (schedules.get("scheduleC") or {}).get("incomeSections") or []:
            rows.append([
                official, year, filing_type,
                "C - Income Source",
                entry.get("nameOfSource", ""),
                fmt_value(entry.get("grossIncomeReceived")),
                entry.get("consideration", ""),
            ])

        # ── Schedule D: Gifts ─────────────────────────────────────────────────
        for entry in (schedules.get("scheduleD") or {}).get("sections") or []:
            for gift in entry.get("gifts") or []:
                rows.append([
                    official, year, filing_type,
                    "D - Gift",
                    entry.get("nameOfSource", ""),
                    f"${gift.get('value', '')}",
                    gift.get("description", ""),
                ])

    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def scrape():
    all_rows     = []
    raw_saved    = False

    for first_name, last_name in SUPERVISORS:
        print(f"\nFetching Form 700s for {first_name} {last_name}...")
        data = fetch_filings(first_name, last_name)

        if data is None:
            print(f"  No data returned.")
            continue

        # Save the first raw response so we can inspect the actual field names
        if not raw_saved:
            with open("raw_response.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            print("  Saved raw API response to raw_response.json (inspect to verify field names)")
            raw_saved = True

        rows = extract_rows(data, first_name, last_name)
        print(f"  Found {len(rows)} interest entries")
        all_rows.extend(rows)
        time.sleep(SLEEP_SEC)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Official Name",
            "Filing Year",
            "Filing Type",
            "Schedule",
            "Name of Business Entity or Source",
            "Fair Market Value",
            "Nature of Investment or Interest",
        ])
        for row in all_rows:
            writer.writerow(row)

    print(f"\nDone. {len(all_rows)} entries written to {CSV_FILE}")
    if not all_rows:
        print("  No entries extracted — open raw_response.json to inspect the API response structure")
        print("  and adjust the field names in extract_rows() to match.")


if __name__ == "__main__":
    scrape()
