"""FastAPI entrypoint for WhatsApp Bot AI."""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.settings import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/")
async def health_check() -> dict[str, str]:
    """Simple health endpoint to validate service status."""
    return {"status": "ok", "message": "WhatsApp Bot AI backend is running"}


# Mount API v1 routes under /api/v1.
app.include_router(api_router, prefix="/api/v1")

