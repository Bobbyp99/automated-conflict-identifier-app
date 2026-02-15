from fastapi import FastAPI

app = FastAPI()

# From Neil!
@app.get("/")
def read_root():
    return {"status": "API is running"}