import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BASE = "https://publicdocs.santa-ana.org/WebLink/"
CSV_FILE = "scraped_data.csv"
CURRENT_YEAR = datetime.now().year
ALLOWED_YEARS = {CURRENT_YEAR, CURRENT_YEAR - 1}
MIN_YEARS = CURRENT_YEAR - 5
YEAR_RANGE_FOLDER = False

def get_soup(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Request failed: {url} | {e}")
        return None


def extract_year(text):
    try:
        return str("".join(filter(str.isdigit, text)))
    except:
        return None


def load_existing_links(csv_file):
    links = set()

    if not os.path.exists(csv_file):
        return links

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header

        for row in reader:
            if len(row) > 2:
                links.add(row[2])  # File Link column

    return links


def scrape_files(folder_link, writer, path, existing_links, incremental):
    soup = get_soup(folder_link)
    if not soup:
        return False

    total_entries_tag = soup.find("span", class_="PageableListTotal")
    if not total_entries_tag:
        return False

    total_entries = int("".join(filter(str.isdigit, total_entries_tag.text)))

    # FULL SCRAPE
    if not incremental:
        for num in range(1, total_entries + 1, 25):
            row_url = folder_link.replace("Row1.aspx", f"Row{num}.aspx")
            soup = get_soup(row_url)
            if not soup:
                continue

            table = soup.find("table", class_="DocumentBrowserDisplayTable")
            if not table:
                continue

            rows = table.find_all("tr")[1:]

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                href = cols[0].a.get("href", "")

                # Only include actual files
                if ("/doc/" not in href) and ("/edoc" not in href):
                    continue

                file_name = cols[0].a["aria-label"]
                file_page_count = cols[1]["aria-label"]
                file_page_count = int("".join(filter(str.isdigit, file_page_count)))
                file_link = BASE + href
                file_date_create = cols[3]["aria-label"]
                file_date_modified = cols[4]["aria-label"]

                writer.writerow([
                    file_name,
                    file_page_count,
                    file_link,
                    file_date_create,
                    file_date_modified,
                    " > ".join(path)
                ])

        return False

    # NEW FILES
    stack = []

    for num in range(1, total_entries + 1, 25):
        row_url = folder_link.replace("Row1.aspx", f"Row{num}.aspx")
        soup = get_soup(row_url)
        if not soup:
            continue

        table = soup.find("table", class_="DocumentBrowserDisplayTable")
        if not table:
            continue

        rows = table.find_all("tr")[1:]

        found_existing = False

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            try:
                href = cols[0].a.get("href", "")

                # Only include actual files
                if ("/doc/" not in href) and ("/edoc" not in href):
                    continue

                file_name = cols[0].a["aria-label"]
                file_page_count = cols[1]["aria-label"]
                file_page_count = int("".join(filter(str.isdigit, file_page_count)))
                file_link = (BASE + href).strip().rstrip("/")
                file_date_create = cols[3]["aria-label"]
                file_date_modified = cols[4]["aria-label"]

                # Stop condition (but finish page first)
                if file_link in existing_links:
                    found_existing = True
                    continue

                stack.append([
                    file_name,
                    file_page_count,
                    file_link,
                    file_date_create,
                    file_date_modified,
                    " > ".join(path)
                ])

            except:
                continue

        # Stop AFTER finishing the page
        if found_existing:
            break

    # Write collected new files
    for item in stack:
        writer.writerow(item)

    return False

def process_folder(folder_link, writer, path, existing_links, ALLOWED_YEARS, incremental):
    soup = get_soup(folder_link)
    if not soup:
        return

    # Scrape files in this folder
    scrape_files(folder_link, writer, path, existing_links, incremental)

    # Traverse subfolders, filter files out
    subfolders = [
        sub for sub in soup.find_all("a", class_="DocumentBrowserNameLink")
        if "/fol/" in sub.get("href", "")
    ]

    for sub in subfolders:
        name = sub.get("aria-label", "")
        sub_link = BASE + sub["href"]

        yearAll = extract_year(name)
        yearStart = int(yearAll[:4]) if len(yearAll) >= 4 else 0
        yearEnd = int(yearAll[4:]) if len(yearAll) > 4 else 0

        # If incremental mode → only current + last year
        if incremental:
            if yearStart in ALLOWED_YEARS or yearEnd in ALLOWED_YEARS:
                new_path = path + [name]
                process_folder(sub_link, writer, new_path, existing_links, ALLOWED_YEARS, incremental)

        else:
            # First run: allow all reasonable years and folders without years
            if (yearStart > MIN_YEARS or yearEnd > MIN_YEARS) or (yearStart == 0 and yearEnd == 0):
                new_path = path + [name]
                process_folder(sub_link, writer, new_path, existing_links, ALLOWED_YEARS, incremental)
            else:
                # Look through most recent folder if file name is a range
                if yearEnd == 0 and "-" in name:
                    new_path = path + [name]
                    process_folder(sub_link, writer, new_path, existing_links, ALLOWED_YEARS, incremental)

def find_folders_and_files():
    start_url = "https://publicdocs.santa-ana.org/WebLink/1/fol/4/Row1.aspx"

    soup = get_soup(start_url)
    if not soup:
        return

    existing_links = load_existing_links(CSV_FILE)
    incremental = len(existing_links) > 0
    mode = "a" if incremental else "w"

    print("\n=== RUN MODE ===")
    print("Incremental update" if incremental else "Full scrape")
    print("================\n")

    with open(CSV_FILE, mode, newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not incremental:
            writer.writerow([
                "File Name",
                "Page count",
                "File Link",
                "Date Created",
                "Date Modified",
                "Path"
            ])

        commissions = soup.find_all("a", class_="DocumentBrowserNameLink")

        for com in commissions:
            commission_name = com.get("aria-label", "Unknown Commission")
            commission_link = BASE + com["href"]

            print(f"\n=== Commission: {commission_name} ===")

            process_folder(
                commission_link,
                writer,
                [commission_name],
                existing_links,
                ALLOWED_YEARS,
                incremental
            )

    print("\nDone.")

# relevant
find_folders_and_files()