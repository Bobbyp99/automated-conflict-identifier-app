from fastapi import FastAPI

app = FastAPI()

# From Neil! In branch test v2, no less!
@app.get("/")
def read_root():
    return {"status": "API is running"}