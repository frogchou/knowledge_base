from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.ui.routes import ui_router
from app.db.models import Base
from app.db.session import engine
import asyncio

setup_logging()

app = FastAPI(title="Knowledge Base", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"success": True, "data": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "internal_error", "message": str(exc)}},
    )


app.include_router(api_router, prefix="/api/v1")
app.include_router(ui_router, prefix="/ui")
