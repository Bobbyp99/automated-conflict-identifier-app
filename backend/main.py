from fastapi import FastAPI

app = FastAPI()

# From Neil! In branch test v2, no less!
# From Andi! Testing to see if git is working in test3 now!
# From Andi again! And again from my Windows PC!
# Testing one last time for good measure.
@app.get("/")
def read_root():
    return {"status": "API is running"}