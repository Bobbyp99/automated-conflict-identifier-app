from fastapi import FastAPI
import requests
import json
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
def read_root():
    html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document</title>
        </head>
        <body>
            <h1>hi</h1>
            <form action="/Form700" method="get">
                <div>
                    <label>Agency</label>
                    <input type="text" name="agency" placeholder="Agency"/>
                </div>
                <div>
                    <label>First Name</label>
                    <input type="text" name="first_name" placeholder="First Name"/>
                </div>
                <div>
                    <label>Last Name</label>
                    <input type="text" name="last_name" placeholder="Last Name"/>
                </div>
                <div>
                    <label>Interest</label>
                    <input type="text" name="interest" placeholder="interest"/>
                </div>
                <div>
                    <label>year</label>
                    <input type="number" name="year" placeholder="year"/>
                </div>
                <button>search</button>
            </form>
        </body>
        </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/Form700")
def search_form700(agency:str = "", first_name: str = "", last_name: str = "", year:str = None, interest: str = ""):
    """
        This is used to search through form 700s,\n

        url is in the form: \n
        localhost:8000/Form700?param=val&param=val&param=val...\n

        order doesn't matter\n\n

        Examples:\n
        localhost:8000/Form700?name=paul\n
        localhost:8000/Form700?agency=sacramento&name=paul\n
        localhost:8000/Form700?agency=sacramento&interest=APPL\n
        localhost:8000/Form700?name=paul&agency=sacramento&interest=APPL\n
    """


    year = int(year) if year.isdigit() else None

    # url, post request
    URL = "https://form700search.fppc.ca.gov/Home/SearchDocuments"
    # Payload
    payload = {
    "queryGenerationInfo": None,
    "searchFieldQueryInfos":
      [
          {"queryField":"FilerAgency","filterValue": agency},
          {"queryField":"FilerFirstName","queryType":"Start With","filterValue":first_name},
          {"queryField":"FilerLastName","queryType":"Start With","filterValue":last_name},
          {"queryField":"FilingType","filterValue":[]},
          {"queryField":"ScheduleA1MultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleA1Comments","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleA2MultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleA2Comments","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleBMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleBComments","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleCIncomeMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleCLoanMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleCComments","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleDMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleDGiftsMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleDComments","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleEMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"ScheduleEComments","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"Attachment700PMultiFields","filterValue":interest,"queryType":"MultiFields Exact Phrase"},
          {"queryField":"Attachment700PComments","filterValue":interest,"queryType":"MultiFields Exact Phrase"}
      ]
    ,"showOnlyHeldPositions": False
    }


    if year:
        payload.get("searchFieldQueryInfos").append({"queryField":"FilingYear","filterValue":year})


    response = requests.post(URL, json=payload).json()
    data: dict = json.loads(response)

    return data
