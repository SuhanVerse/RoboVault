from fastapi import FastAPI

from app.api.routes import auth, items, loans, ocr
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Inventory and equipment lending API for the robotics club.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(loans.router)
app.include_router(ocr.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Liveness probe used by Docker and CI."""
    return {"status": "ok"}
