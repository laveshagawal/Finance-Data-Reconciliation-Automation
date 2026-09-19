from fastapi import FastAPI

app = FastAPI(
    title="Finance Data Reconciliation API",
    description="Automated financial transaction reconciliation",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Finance Data Reconciliation API is running",
        "status": "online"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
