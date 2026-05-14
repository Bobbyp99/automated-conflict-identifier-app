"""
scanner.py — Background conflict scanner for the API.

Same logic as conflictScanner.py, but:
  - takes in-memory row lists (from uploaded CSVs) instead of reading files
  - writes results to SQLite via ScanJob / ConflictResult models
  - updates ScanJob progress as it goes so the frontend can poll it
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime
from sqlalchemy.orm import Session

from models import ScanJob, ConflictResult

# ── Config (mirrors conflictScanner.py) ──────────────────────────────────────
SLEEP_SEC      = 1.5
MIN_ENTITY_LEN = 5
YEAR_WINDOW    = 1

SKIP_ENTITIES = {"", "other", "salary", "stock", "ownership/deed of trust"}

CEREMONIAL_PATTERNS = re.compile(
    r"adopt a (gold |silver )?resolution|proclamation|honoring|commending|"
    r"recognizing|in memory of|in honor of",
    re.IGNORECASE,
)


# ── Column auto-detection ─────────────────────────────────────────────────────

def _col(row: dict, *keywords: str) -> str:
    """Return the value from the first column whose name contains any keyword."""
    for kw in keywords:
        for k in row:
            if kw.lower() in k.lower():
                return row[k]
    return ""


# ── Interest loading (identical filters to conflictScanner.load_interests) ────

def load_interests(rows: list) -> dict:
    interests = defaultdict(list)
    for row in rows:
        schedule = _col(row, "schedule")
        if schedule.startswith("D"):
            continue

        official = _col(row, "official", "filer", "name").strip()
        entity   = _col(row, "entity", "business", "source").strip()
        year     = _col(row, "filing year", "year")

        if len(entity) < MIN_ENTITY_LEN:
            continue
        if entity.lower() in SKIP_ENTITIES:
            continue
        if entity.lower() == official.lower():
            continue

        name_parts = {p.lower() for p in official.split()}
        if entity.lower() in name_parts:
            continue
        if "dissolved" in entity.lower():
            continue
        if " " not in entity and len(entity) < 8:
            continue

        official_last = official.split()[-1].lower() if official.split() else ""
        core = re.split(r'\s*\(', entity)[0].strip()
        core_words = core.split()
        if len(core_words) >= 2 and core_words[-1].lower() == official_last:
            continue

        interests[official].append({"entity": entity, "year": year, "schedule": schedule})

    return interests


# ── Page fetching (identical to conflictScanner.fetch_page_text) ──────────────

def fetch_page_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return ""


# ── Entity matching (identical to conflictScanner.entity_matches) ─────────────

def entity_matches(entity: str, text: str) -> bool:
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


# ── Progress helper ───────────────────────────────────────────────────────────

def _save_progress(engine, job_id: str, processed: int, flagged: int):
    with Session(engine) as db:
        job = db.get(ScanJob, job_id)
        if job:
            job.processed = processed
            job.flagged   = flagged
            db.commit()


# ── Main background function ──────────────────────────────────────────────────

def run_scan(job_id: str, interests_rows: list, decisions_rows: list, engine):
    """
    Runs in a daemon thread. Mirrors conflictScanner.scan() exactly:
    loads interests, groups decisions by URL, fetches each Legistar page,
    and searches for entity names in the full page body text.
    """
    try:
        interests = load_interests(interests_rows)

        # Group decisions by URL (one page fetch covers all voters on that matter)
        by_url = defaultdict(list)
        for row in decisions_rows:
            url = _col(row, "link", "url")
            if url:
                by_url[url].append(row)

        unique_urls = list(by_url.keys())
        total = len(unique_urls)

        with Session(engine) as db:
            job = db.get(ScanJob, job_id)
            if job:
                job.status = "running"
                job.total  = total
                db.commit()

        flagged = 0
        seen    = set()  # deduplicate: (official, entity, file_number)

        for i, url in enumerate(unique_urls, 1):
            vote_rows = by_url[url]
            sample    = vote_rows[0]

            subject  = _col(sample, "agenda item subject", "subject", "title")
            file_num = _col(sample, "file number", "file")

            # Skip ceremonial matters — no financial interest possible
            if CEREMONIAL_PATTERNS.search(subject):
                _save_progress(engine, job_id, i, flagged)
                continue

            text = fetch_page_text(url)
            if not text:
                time.sleep(SLEEP_SEC)
                _save_progress(engine, job_id, i, flagged)
                continue

            try:
                vote_year = int(_col(sample, "vote date", "date")[:4])
            except (ValueError, TypeError):
                vote_year = None

            with Session(engine) as db:
                for vote_row in vote_rows:
                    official = _col(vote_row, "official", "name").strip()
                    outcome  = _col(vote_row, "vote outcome", "outcome").strip()

                    if outcome == "Absent":
                        continue

                    for interest in interests.get(official, []):
                        try:
                            if vote_year and abs(int(interest["year"]) - vote_year) > YEAR_WINDOW:
                                continue
                        except (ValueError, TypeError):
                            pass

                        if not entity_matches(interest["entity"], text):
                            continue

                        dedup_key = (official, interest["entity"], file_num)
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

                        db.add(ConflictResult(
                            job_id            = job_id,
                            official_name     = official,
                            vote_outcome      = outcome,
                            file_number       = file_num,
                            subject           = subject,
                            vote_date         = _col(vote_row, "vote date", "date"),
                            meeting_type      = _col(vote_row, "meeting type", "meeting"),
                            overall_result    = _col(vote_row, "overall result", "result"),
                            entity_matched    = interest["entity"],
                            interest_schedule = interest["schedule"],
                            interest_year     = interest["year"],
                            link              = url,
                        ))
                        flagged += 1
                        print(f"  *** FLAGGED: {official} — {interest['entity']}")

                job = db.get(ScanJob, job_id)
                if job:
                    job.processed = i
                    job.flagged   = flagged
                    db.commit()

            time.sleep(SLEEP_SEC)

        # Mark complete
        with Session(engine) as db:
            job = db.get(ScanJob, job_id)
            if job:
                job.status       = "done"
                job.flagged      = flagged
                job.completed_at = datetime.utcnow()
                db.commit()

        print(f"Scan {job_id[:8]} complete — {flagged} conflicts found.")

    except Exception as e:
        print(f"Scan {job_id[:8]} error: {e}")
        with Session(engine) as db:
            job = db.get(ScanJob, job_id)
            if job:
                job.status    = "error"
                job.error_msg = str(e)
                db.commit()
