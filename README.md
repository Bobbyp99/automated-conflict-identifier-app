# FPPC Conflict Analyzer

A web app for identifying potential conflicts of interest between
government employees' disclosed financial interests (Form 700) and
their voting/decision records.

## Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Backend  | Python · FastAPI · SQLAlchemy     |
| Database | SQLite (file: `fppc.db`)          |
| Frontend | Vanilla JavaScript · HTML · CSS   |

---

## Setup

### 1. Install dependencies

```bash
cd fppc_app
pip install -r requirements.txt
```

### 2. Start the backend

```bash
cd backend
uvicorn main:app --reload
```

The API will be live at **http://localhost:8000**
Interactive API docs at **http://localhost:8000/docs**

### 3. Open the app

Visit **http://localhost:8000** in your browser.

---

## How to use

1. **Upload** your interests CSV (Form 700 / Schedule A) and your votes/decisions CSV
2. **Map columns** — the app auto-detects the right columns but lets you override
3. **Run analysis** — results are scored, tiered (High / Medium / Low), and saved to the database
4. **Past Runs tab** — reload any previous analysis from the database

---

## API Endpoints

| Method | Path                      | Description                          |
|--------|---------------------------|--------------------------------------|
| POST   | `/api/upload`             | Upload a CSV file                    |
| GET    | `/api/datasets`           | List uploaded datasets               |
| DELETE | `/api/datasets/{id}`      | Delete a dataset                     |
| POST   | `/api/analyze`            | Run conflict analysis                |
| GET    | `/api/results/{run_id}`   | Fetch results for a run (filterable) |
| GET    | `/api/runs`               | List all past runs                   |

---

## Upgrading to PostgreSQL

In `backend/main.py`, change:

```python
engine = get_engine("sqlite:///./fppc.db")
```

to:

```python
engine = get_engine("postgresql://user:password@localhost/fppc")
```

Then `pip install psycopg2-binary`.

---

## Project Structure

```
fppc_app/
├── backend/
│   ├── main.py       # FastAPI routes
│   ├── models.py     # SQLAlchemy ORM models
│   └── matcher.py    # Conflict scoring engine
├── frontend/
│   ├── index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
└── requirements.txt
```
