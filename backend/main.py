"""
main.py — FPPC Conflict Analyzer API

Endpoints:
  POST /api/upload          Upload a CSV (interests or votes)
  GET  /api/datasets        List all uploaded datasets
  DELETE /api/datasets/{id} Delete a dataset and its rows
  GET  /api/columns/{id}    Get column headers for a dataset
  POST /api/analyze         Run conflict analysis, persist + return results
  GET  /api/results/{run_id} Fetch a previously saved analysis run
  GET  /api/runs            List all past analysis runs
"""

import csv
import io
import json
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from models import Dataset, Interest, Vote, ConflictResult, get_engine, init_db
from matcher import run_match

# ── App setup ────────────────────────────────────────────────
app = FastAPI(title="FPPC Conflict Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = get_engine()
init_db(engine)


def get_db():
    with Session(engine) as session:
        yield session


# ── Helpers ──────────────────────────────────────────────────

def parse_csv_bytes(content: bytes) -> tuple[list[str], list[dict]]:
    """Return (headers, rows) from raw CSV bytes."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = [dict(r) for r in reader]
    return list(headers), rows


def best_col(headers: list[str], candidates: list[str]) -> str:
    """Return first header that contains any candidate substring (case-insensitive)."""
    for c in candidates:
        for h in headers:
            if c in h.lower():
                return h
    return headers[0] if headers else ""


# ── Upload ────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_csv(
    file: UploadFile = File(...),
    kind: str = Form(...),          # "interests" or "votes"
    db: Session = Depends(get_db),
):
    if kind not in ("interests", "votes"):
        raise HTTPException(400, "kind must be 'interests' or 'votes'")

    content = await file.read()
    headers, rows = parse_csv_bytes(content)

    if not rows:
        raise HTTPException(400, "CSV appears empty")

    dataset = Dataset(name=file.filename, kind=kind, row_count=len(rows))
    db.add(dataset)
    db.flush()  # get dataset.id

    if kind == "interests":
        emp_col    = best_col(headers, ["last name", "employee", "name", "filer", "person"])
        entity_col = best_col(headers, ["name of business", "entity", "org", "company", "source"])
        type_col   = best_col(headers, ["nature", "type", "investment", "activity", "description"])
        fmv_col    = best_col(headers, ["fair market", "fmv", "value"])
        for row in rows:
            db.add(Interest(
                dataset_id = dataset.id,
                employee   = (row.get(emp_col) or "").strip(),
                entity     = (row.get(entity_col) or "").strip(),
                inv_type   = (row.get(type_col) or "").strip(),
                fmv        = (row.get(fmv_col) or "").strip(),
                raw_json   = json.dumps(row),
            ))
    else:
        emp_col  = best_col(headers, ["employee", "name", "filer", "voter", "official"])
        sub_col  = best_col(headers, ["subject", "matter", "title", "agenda", "item", "description"])
        date_col = best_col(headers, ["date", "filed", "created", "action", "period"])
        for row in rows:
            db.add(Vote(
                dataset_id = dataset.id,
                employee   = (row.get(emp_col) or "").strip(),
                subject    = (row.get(sub_col) or "").strip(),
                vote_date  = (row.get(date_col) or "").strip(),
                raw_json   = json.dumps(row),
            ))

    db.commit()
    return {
        "id":       dataset.id,
        "name":     dataset.name,
        "kind":     dataset.kind,
        "rows":     dataset.row_count,
        "headers":  headers,
        "guessed":  {
            "employee": emp_col if kind == "interests" else emp_col,
            "entity":   entity_col if kind == "interests" else None,
            "subject":  sub_col if kind == "votes" else None,
        }
    }


# ── Datasets ──────────────────────────────────────────────────

@app.get("/api/datasets")
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
    return [
        {"id": d.id, "name": d.name, "kind": d.kind,
         "rows": d.row_count, "uploaded_at": d.uploaded_at.isoformat()}
        for d in datasets
    ]


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    d = db.get(Dataset, dataset_id)
    if not d:
        raise HTTPException(404, "Dataset not found")
    db.delete(d)
    db.commit()
    return {"deleted": dataset_id}


@app.get("/api/columns/{dataset_id}")
def get_columns(dataset_id: int, db: Session = Depends(get_db)):
    d = db.get(Dataset, dataset_id)
    if not d:
        raise HTTPException(404, "Dataset not found")
    if d.kind == "interests":
        row = db.query(Interest).filter_by(dataset_id=dataset_id).first()
    else:
        row = db.query(Vote).filter_by(dataset_id=dataset_id).first()
    if not row:
        return {"columns": []}
    return {"columns": list(json.loads(row.raw_json).keys())}


# ── Analyze ───────────────────────────────────────────────────

@app.post("/api/analyze")
def analyze(
    body: dict,
    db: Session = Depends(get_db),
):
    """
    body = {
      interests_dataset_id: int,
      votes_dataset_id: int,
      col_employee_interests: str,   # optional overrides
      col_entity: str,
      col_employee_votes: str,
      col_subject: str,
    }
    """
    i_id = body.get("interests_dataset_id")
    v_id = body.get("votes_dataset_id")

    if not i_id or not v_id:
        raise HTTPException(400, "Both dataset IDs are required")

    interests = db.query(Interest).filter_by(dataset_id=i_id).all()
    votes     = db.query(Vote).filter_by(dataset_id=v_id).all()

    # Column overrides: re-read raw_json and remap fields if caller specified columns
    col_emp_i = body.get("col_employee_interests")
    col_ent   = body.get("col_entity")
    col_emp_v = body.get("col_employee_votes")
    col_sub   = body.get("col_subject")

    if col_emp_i or col_ent:
        for obj in interests:
            raw = json.loads(obj.raw_json)
            if col_emp_i: obj.employee = (raw.get(col_emp_i) or "").strip()
            if col_ent:   obj.entity   = (raw.get(col_ent)   or "").strip()

    if col_emp_v or col_sub:
        for obj in votes:
            raw = json.loads(obj.raw_json)
            if col_emp_v: obj.employee = (raw.get(col_emp_v) or "").strip()
            if col_sub:   obj.subject  = (raw.get(col_sub)   or "").strip()

    matches = run_match(interests, votes)

    run_id = str(uuid.uuid4())
    for m in matches:
        db.add(ConflictResult(run_id=run_id, **m))
    db.commit()

    return {"run_id": run_id, "count": len(matches), "matches": matches}


# ── Results ───────────────────────────────────────────────────

@app.get("/api/results/{run_id}")
def get_results(
    run_id: str,
    likelihood: Optional[str] = None,
    employee: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ConflictResult).filter_by(run_id=run_id)
    if likelihood:
        q = q.filter(ConflictResult.likelihood == likelihood)
    if employee:
        q = q.filter(ConflictResult.employee == employee)
    if search:
        like = f"%{search}%"
        q = q.filter(
            ConflictResult.employee.ilike(like) |
            ConflictResult.entity.ilike(like) |
            ConflictResult.subject.ilike(like)
        )
    rows = q.order_by(ConflictResult.score.desc()).all()
    return [
        {
            "employee":    r.employee,
            "entity":      r.entity,
            "entity_type": r.entity_type,
            "subject":     r.subject,
            "vote_date":   r.vote_date,
            "score":       r.score,
            "likelihood":  r.likelihood,
        }
        for r in rows
    ]


@app.get("/api/runs")
def list_runs(db: Session = Depends(get_db)):
    rows = (
        db.query(
            ConflictResult.run_id,
            ConflictResult.created_at,
        )
        .distinct(ConflictResult.run_id)
        .order_by(ConflictResult.created_at.desc())
        .all()
    )
    results = []
    for run_id, created_at in rows:
        count = db.query(ConflictResult).filter_by(run_id=run_id).count()
        high  = db.query(ConflictResult).filter_by(run_id=run_id, likelihood="High").count()
        results.append({
            "run_id":     run_id,
            "created_at": created_at.isoformat(),
            "count":      count,
            "high":       high,
        })
    return results


# ── Serve frontend ────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("../frontend/index.html")
