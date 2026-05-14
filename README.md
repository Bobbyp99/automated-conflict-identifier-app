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
pip install -r requirements.txt
```

### 2. Start the backend

```bash
venv\Scripts\activate
cd backend
uvicorn main:app --reload
```

The API will be live at **http://localhost:8000**
Interactive API docs at **http://localhost:8000/docs**

### 3. Configure scrapers
- in webScraperLegistar.py, change "COUNTY_NAME" to desired county (default is sonoma-county)
- in form700Scraper.py, change SUPERVISORS and agency (default are "Sonoma County Board of Supervisors" and "Sonoma County", respectively)
- change destination file name is desired

### 4. Run Scrapers
- run the scrapers in the terminal
- note the destination csv files

### 4. Open the app

Visit **http://localhost:8000** in your browser.

---

## How to use

1. **Upload** your interests CSV (Form 700 / Sc) and your votes/decisions CSV
2. **Run analysis** — results are scored, tiered (High / Medium / Low), and saved to the database
3. **Past Runs tab** — reload any previous analysis from the database

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

