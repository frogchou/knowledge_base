from fastapi import APIRouter

from app.api.v1 import auth, items, search

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
