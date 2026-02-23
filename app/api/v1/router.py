"""Main router for API v1."""

from fastapi import APIRouter

from app.api.v1.routes.test import router as test_router

api_router = APIRouter()

# Include test routes for integration checks.
api_router.include_router(test_router, tags=["test"])

