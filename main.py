from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from initialize import init_db
from api import router as api_router
from ui import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager for the lifespan of the FastAPI application."""
    await init_db()
    yield
    # Cleanup if needed


# FastAPI app
app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(ui_router, tags=["ui"])
