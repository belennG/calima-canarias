from fastapi import FastAPI

from calima_api.routers import stations

app = FastAPI(
    title="Calima API",
    description="Backend for Calima Canarias App",
    version="1.0.0"
)

app.include_router(stations.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "API works"
    }