import csv
import io
import uuid
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from models import ScanJob, ConflictResult, get_engine, init_db
from scanner import run_scan

app = FastAPI(title="Conflict of Interest Scanner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = get_engine()
init_db(engine)

# In-memory store for uploaded CSV rows.
# upload_id -> {"filename": str, "kind": str, "rows": list[dict]}
uploads: dict = {}


# ── CSV helper ────────────────────────────────────────────────────────────────

def parse_csv_bytes(data: bytes) -> tuple:
    text   = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows   = list(reader)
    return list(reader.fieldnames or []), rows


# ── Frontend ──────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/")
def index():
    return FileResponse("../frontend/index.html")


# ── Upload ────────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload(file: UploadFile = File(...), kind: str = Form(...)):
    """
    Parse an uploaded CSV and hold its rows in memory.
    kind must be 'interests' or 'votes'.
    Returns an upload_id the client passes to /api/scan.
    """
    raw           = await file.read()
    headers, rows = parse_csv_bytes(raw)
    upload_id     = str(uuid.uuid4())

    uploads[upload_id] = {
        "filename": file.filename,
        "kind":     kind,
        "rows":     rows,
    }

    return {
        "id":      upload_id,
        "name":    file.filename,
        "kind":    kind,
        "rows":    len(rows),
        "columns": headers,
    }


# ── Scan lifecycle ────────────────────────────────────────────────────────────

@app.post("/api/scan")
def start_scan(body: dict):
    """
    Start a background conflict scan.
    Body: {"interests_id": "<upload_id>", "votes_id": "<upload_id>"}
    Returns {"job_id": "<uuid>"} immediately — poll /api/scan/{job_id} for progress.
    """
    interests_id = body.get("interests_id")
    votes_id     = body.get("votes_id")

    if interests_id not in uploads:
        raise HTTPException(400, "interests_id not found — re-upload the interests file")
    if votes_id not in uploads:
        raise HTTPException(400, "votes_id not found — re-upload the decisions file")

    interests_rows = uploads[interests_id]["rows"]
    decisions_rows = uploads[votes_id]["rows"]

    job_id = str(uuid.uuid4())
    with Session(engine) as db:
        db.add(ScanJob(id=job_id, status="pending", total=0, processed=0, flagged=0))
        db.commit()

    thread = threading.Thread(
        target=run_scan,
        args=(job_id, interests_rows, decisions_rows, engine),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@app.get("/api/scan/{job_id}")
def scan_status(job_id: str):
    """Poll for live scan progress."""
    with Session(engine) as db:
        job = db.get(ScanJob, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return {
            "status":    job.status,
            "total":     job.total,
            "processed": job.processed,
            "flagged":   job.flagged,
            "error":     job.error_msg,
        }


@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    """Return all flagged conflicts for a scan — same fields as flagged_conflicts.csv."""
    with Session(engine) as db:
        rows = db.query(ConflictResult).filter_by(job_id=job_id).all()
        return [
            {
                "official_name":     r.official_name,
                "vote_outcome":      r.vote_outcome,
                "file_number":       r.file_number,
                "subject":           r.subject,
                "vote_date":         r.vote_date,
                "meeting_type":      r.meeting_type,
                "overall_result":    r.overall_result,
                "entity_matched":    r.entity_matched,
                "interest_schedule": r.interest_schedule,
                "interest_year":     r.interest_year,
                "link":              r.link,
            }
            for r in rows
        ]


# ── Past runs ─────────────────────────────────────────────────────────────────

@app.get("/api/runs")
def list_runs():
    """Summary of every scan ever run, newest first."""
    with Session(engine) as db:
        jobs = db.query(ScanJob).order_by(ScanJob.created_at.desc()).all()
        return [
            {
                "job_id":     j.id,
                "status":     j.status,
                "total":      j.total,
                "processed":  j.processed,
                "flagged":    j.flagged,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
