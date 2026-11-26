from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from calima_api.routers import stations

app = FastAPI(
    title="Calima API",
    description="Backend for Calima Canarias App",
    version="1.0.0"
)

# Only the Angular dev server for now; add the deployed frontend's origin once it exists.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET"],
)

app.include_router(stations.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "API works"
    }