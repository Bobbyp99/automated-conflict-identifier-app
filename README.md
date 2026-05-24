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

### 1. Navigate to the backend

```bash
cd backend
pip install -r requirements.txt
```
- everything from this point should be done from the backend

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up the virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```
### SCRAPING (4-5)
### 4. Configure the scraper fields (default is Sonoma County Board of Supervisors)
- in webScraperLegistar.py, change "COUNTY_NAME" to desired county (default is sonoma-county)
- in webScraperLegistar.py, edit the SITE_LINK (usually just replace the county name in the link)
- in form700Scraper.py, change SUPERVISORS and agency (default are "Sonoma County Board of Supervisors" and "Sonoma County", respectively)
- agency must be written the same as listed in the FPPC Form 700 Database (eg. Sacramento)
- change destination file name is desired

### 5. Run Scrapers
- run the scrapers and see activity in the terminal and the csv files as data is being written

### 6. Navigate to the virtually setup WebApp
```bash
uvicorn main:app --reload
```
Visit **http://localhost:8000** in your browser.

The API will be live at **http://localhost:8000**
Interactive API docs at **http://localhost:8000/docs**

## How to use

1. **Upload** your interests CSV (Form 700 / Sc) and your votes/decisions CSV
   NOTE: If you want to upload CSVs acquired through other means, make sure they match the format of the default scraped data of Sonoma County
   in decisions_test6.csv and income_sources2.csv
3. **Run analysis** — results are scored, tiered (High / Medium / Low) based on the match become from Income C, B, or A respectively, and saved to the database
4. **Past Runs tab** — reload any previous analysis from the database

---

## API Endpoints

| Method | Path                      | Description                          |
|--------|---------------------------|--------------------------------------|
| POST   | `/api/upload`             | Upload a CSV file                    |
| GET    | `/api/datasets`           | List uploaded datasets               |
| DELETE | `/api/datasets/{id}`      | Delete a dataset                     |
| POST   | `/api/analyze`            | Run conflict analysis                |
| GET    | `/api/results/{run_id}`   | Fetch 
