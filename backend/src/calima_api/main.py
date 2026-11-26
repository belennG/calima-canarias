from fastapi import FastAPI

app = FastAPI(
    title="Calima API",
    description="Backend for Calima Canarias App",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "API works"
    }