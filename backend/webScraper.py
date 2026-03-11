import csv
import requests
from bs4 import BeautifulSoup

BASE = "https://publicdocs.santa-ana.org/WebLink/"

def scrape_files_from_folder(folder_link, writer):
    page = requests.get(folder_link)
    soup = BeautifulSoup(page.text, "html.parser")

    total_entries = soup.find("span", class_="PageableListTotal").text
    total_entries = int("".join(filter(str.isdigit, total_entries)))

    for num in range(1, total_entries + 1, 25):

        row_url = folder_link.replace("Row1.aspx", f"Row{num}.aspx")

        page = requests.get(row_url)
        soup = BeautifulSoup(page.text, "html.parser")
        table = soup.find("table", class_="DocumentBrowserDisplayTable")
        rows = table.find_all("tr")[1:]

        for data in rows:
            file_date_create = (data.find_all('td')[3:])[0]["aria-label"]
            file_date_modified = (data.find_all('td'))[4:][0]["aria-label"]
            file_name = data.td.a["aria-label"]
            file_link = BASE + data.td.a["href"]

            # Write to CSV
            writer.writerow([
                file_name,
                file_link,
                file_date_create,
                file_date_modified
            ])

def find_folders_and_files():

    start_url = "https://publicdocs.santa-ana.org/WebLink/1/fol/58216/Row1.aspx"
    page = requests.get(start_url)
    soup = BeautifulSoup(page.text, "html.parser")

    total_entries = soup.find("span", class_="PageableListTotal").text
    total_entries = int("".join(filter(str.isdigit, total_entries)))

    print(f"Total folders: {total_entries}, skipping folders older than 2020")

    # Open CSV file
    with open("scraped_data.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Header row
        writer.writerow(["File Name", "File Link", "Date Created", "Date Modified"])
        print("Writing data to csv file")

        for num in range(1, total_entries + 1, 25):
            url = f"https://publicdocs.santa-ana.org/WebLink/1/fol/58216/Row{num}.aspx"

            page = requests.get(url)
            soup = BeautifulSoup(page.text, "html.parser")

            folders = soup.find_all("a", class_="DocumentBrowserNameLink")

            for folder in folders:

                folder_name = folder["aria-label"]

                try:
                    folder_date = int("".join(filter(str.isdigit, folder_name)))
                except:
                    continue

                folder_link = BASE + folder["href"]

                if folder_date > 2020:
                    print(".")
                    scrape_files_from_folder(folder_link, writer)
            print("Done.")

find_folders_and_files()