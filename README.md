# FPPC Conflict Analyzer

A WebApp for identifying potential conflicts of interest between
government employees' disclosed financial interests (Form 700) and
their voting/decision records. There are two scrapers. One is the 
Legistar Scraper which is uses Legistars public API to get matters
voted on in a given local jurisdiction for a set time frame. The 
second scraper is a Form 700 form scraper which uses the FPPC website.
Both of these scrapers write data to a csv file each, and these csv
files will be manually uploaded by the user to the WebApp, where the 
user will then click "Run Conflict Scan" to run the matcher. From 
there, a human can look at the matches below or navigate to the 
"Past Runs" tab where conflict scans are stored.

## Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Backend  | Python · FastAPI · SQLAlchemy     |
| Database | SQLite (file: `fppc.db`)          |
| Frontend | Vanilla JavaScript · HTML · CSS   |

---

## Setup

### 1. Open this project
Clone the repository and open it in a coding environment

### 2. Navigate to the backend

```bash
cd backend
```
- everything from this point should be done from the backend

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create the virtual environment
```bash
python -m venv venv
```
### 5. Activate the virtual environment
```bash
venv\Scripts\activate
```
### SCRAPING (6-7)
### 6. Configure the scraper fields (default is Sonoma County Board of Supervisors)
- in webScraperLegistar.py, change "COUNTY_NAME" to desired county (default is sonoma-county)
- in webScraperLegistar.py, edit the SITE_LINK (usually just replace the county name in the link)
- in form700Scraper.py, change SUPERVISORS and agency (default are "Sonoma County Board of Supervisors" and "Sonoma County", respectively)
- agency must be written the same as listed in the FPPC Form 700 Database (eg. Sacramento)
- change destination file name is desired

### 7. Run Scrapers
- run the scrapers and see activity in the terminal and the csv files as data is being written

### 8. Navigate to the virtually setup WebApp
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
   NOTE: This is where you can further analyze the matches using methods beyond the scope of this project

---

### Additional Tools
1. conflictScanner.py
   - this writes matches and outputs them to a csv file with the following fields:
   "Official Name,Vote Outcome,File Number,Agenda Item Subject,Vote Date,Meeting Type,Overall Result,Entity Matched,Interest Schedule,Interest Year,Link"
   - fields must be configured for the name of the decisions and interests files

## Constraints/Limitations
- Extracts data from CSV files for the matching
- Flags for specific counties, not entire cities–Sonoma County matches with Sonoma agenda data.
- The Legistar scraper needs counties that use Legistar’s agenda management system as opposed to any other agenda management system
- The Past Runs are stored on the local fppc db file (however we set up PostgresSQL as an option for you to look into if desired)
- The matcher uses web scraping and entity matching using each decision's Legistar Page, leading to some false positives that are
  only detectable by a human looking at it


## API Endpoints

| Method | Path                      | Description                          |
|--------|---------------------------|--------------------------------------|
| POST   | `/api/upload`             | Upload a CSV file                    |
| GET    | `/api/datasets`           | List uploaded datasets               |
| DELETE | `/api/datasets/{id}`      | Delete a dataset                     |
| POST   | `/api/analyze`            | Run conflict analysis                |
| GET    | `/api/results/{run_id}`   | Fetch 
